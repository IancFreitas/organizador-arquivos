"""Planejamento, execução e reversão da organização de uma pasta."""

from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from organizador.config import FALLBACK_CATEGORY, IGNORED_SUFFIXES

HISTORY_FILE = ".organizador-historico.json"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path


def plan_moves(
    folder: Path,
    extension_map: dict[str, str],
    *,
    by_date: bool = False,
    min_age_seconds: float = 0,
) -> list[Move]:
    """Calcula para onde cada arquivo da pasta deve ir, sem mover nada.

    Apenas arquivos do primeiro nível são considerados; subpastas (incluindo as
    de categorias já criadas) ficam intactas. Arquivos modificados há menos de
    ``min_age_seconds`` são ignorados, pois ainda podem estar sendo gravados.
    """
    moves: list[Move] = []
    reserved: set[Path] = set()
    now = time.time()

    for path in sorted(folder.iterdir()):
        if not _should_organize(path):
            continue

        modified_at = path.stat().st_mtime
        if min_age_seconds > 0 and now - modified_at < min_age_seconds:
            continue

        target_dir = folder / extension_map.get(path.suffix.lower(), FALLBACK_CATEGORY)
        if by_date:
            target_dir /= f"{datetime.fromtimestamp(modified_at):%Y-%m}"

        destination = _unique_destination(target_dir / path.name, reserved)
        reserved.add(destination)
        moves.append(Move(path, destination))

    return moves


def apply_moves(folder: Path, moves: list[Move]) -> None:
    """Move os arquivos e registra a operação no histórico para permitir desfazer."""
    done: list[Move] = []
    try:
        for move in moves:
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(move.source, move.destination)
            done.append(move)
            logger.info("%s -> %s", move.source.name, move.destination.relative_to(folder))
    finally:
        # Mesmo que um arquivo falhe no meio, o que já foi movido fica registrado.
        if done:
            _append_history(folder, done)


def undo_last(folder: Path) -> list[Move]:
    """Desfaz a última organização registrada e retorna os arquivos restaurados."""
    history = _load_history(folder)
    if not history:
        return []

    last_run = history.pop()
    restored: list[Move] = []
    for item in reversed(last_run["moves"]):
        current = folder / item["destination"]
        original = folder / item["source"]

        if not current.exists():
            logger.warning("Ignorado: %s não existe mais.", item["destination"])
            continue
        if original.exists():
            logger.warning("Ignorado: já existe um arquivo em %s.", item["source"])
            continue

        shutil.move(current, original)
        restored.append(Move(current, original))
        logger.info("%s -> %s", item["destination"], item["source"])
        _remove_empty_parents(current.parent, stop_at=folder)

    _save_history(folder, history)
    return restored


def _should_organize(path: Path) -> bool:
    return (
        path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() not in IGNORED_SUFFIXES
    )


def _unique_destination(candidate: Path, reserved: set[Path]) -> Path:
    """Evita sobrescrever arquivos: ``foto.jpg`` vira ``foto (1).jpg`` e assim por diante."""
    destination = candidate
    counter = 1
    while destination.exists() or destination in reserved:
        destination = candidate.with_name(f"{candidate.stem} ({counter}){candidate.suffix}")
        counter += 1
    return destination


def _remove_empty_parents(directory: Path, stop_at: Path) -> None:
    while directory != stop_at and directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
        directory = directory.parent


def _history_path(folder: Path) -> Path:
    return folder / HISTORY_FILE


def _load_history(folder: Path) -> list[dict]:
    path = _history_path(folder)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_history(folder: Path, history: list[dict]) -> None:
    path = _history_path(folder)
    if history:
        path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def _append_history(folder: Path, moves: list[Move]) -> None:
    history = _load_history(folder)
    history.append(
        {
            "executado_em": datetime.now().isoformat(timespec="seconds"),
            "moves": [
                {
                    "source": move.source.relative_to(folder).as_posix(),
                    "destination": move.destination.relative_to(folder).as_posix(),
                }
                for move in moves
            ],
        }
    )
    _save_history(folder, history)
