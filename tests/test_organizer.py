import json
import os
import time
from pathlib import Path

import pytest

from organizador.config import ConfigError, build_extension_map, load_extension_map
from organizador.organizer import HISTORY_FILE, apply_moves, plan_moves, undo_last

EXTENSIONS = load_extension_map()


def make_files(folder: Path, *names: str) -> None:
    for name in names:
        (folder / name).write_text(f"conteúdo de {name}", encoding="utf-8")


def test_files_are_grouped_by_category(tmp_path):
    make_files(tmp_path, "foto.JPG", "contrato.pdf", "vendas.xlsx", "misterio.xyz")

    apply_moves(tmp_path, plan_moves(tmp_path, EXTENSIONS))

    assert (tmp_path / "Imagens" / "foto.JPG").is_file()
    assert (tmp_path / "Documentos" / "contrato.pdf").is_file()
    assert (tmp_path / "Planilhas" / "vendas.xlsx").is_file()
    assert (tmp_path / "Outros" / "misterio.xyz").is_file()


def test_plan_does_not_touch_the_disk(tmp_path):
    make_files(tmp_path, "foto.png")

    moves = plan_moves(tmp_path, EXTENSIONS)

    assert len(moves) == 1
    assert (tmp_path / "foto.png").is_file()
    assert not (tmp_path / "Imagens").exists()


def test_existing_files_are_never_overwritten(tmp_path):
    (tmp_path / "Imagens").mkdir()
    (tmp_path / "Imagens" / "foto.png").write_text("antiga", encoding="utf-8")
    make_files(tmp_path, "foto.png")

    apply_moves(tmp_path, plan_moves(tmp_path, EXTENSIONS))

    assert (tmp_path / "Imagens" / "foto.png").read_text(encoding="utf-8") == "antiga"
    assert (tmp_path / "Imagens" / "foto (1).png").is_file()


def test_ignores_hidden_files_folders_and_partial_downloads(tmp_path):
    make_files(tmp_path, ".oculto.txt", "filme.mp4.crdownload", "arquivo.part")
    (tmp_path / "subpasta").mkdir()

    assert plan_moves(tmp_path, EXTENSIONS) == []


def test_recent_files_are_skipped_when_min_age_is_set(tmp_path):
    make_files(tmp_path, "novo.pdf", "velho.pdf")
    old = time.time() - 60
    os.utime(tmp_path / "velho.pdf", (old, old))

    moves = plan_moves(tmp_path, EXTENSIONS, min_age_seconds=30)

    assert [m.source.name for m in moves] == ["velho.pdf"]


def test_by_date_creates_year_month_subfolders(tmp_path):
    make_files(tmp_path, "relatorio.pdf")
    timestamp = time.mktime((2024, 3, 15, 12, 0, 0, 0, 0, -1))
    os.utime(tmp_path / "relatorio.pdf", (timestamp, timestamp))

    apply_moves(tmp_path, plan_moves(tmp_path, EXTENSIONS, by_date=True))

    assert (tmp_path / "Documentos" / "2024-03" / "relatorio.pdf").is_file()


def test_undo_restores_files_and_removes_empty_folders(tmp_path):
    make_files(tmp_path, "foto.png", "notas.txt")
    apply_moves(tmp_path, plan_moves(tmp_path, EXTENSIONS))

    restored = undo_last(tmp_path)

    assert len(restored) == 2
    assert (tmp_path / "foto.png").is_file()
    assert (tmp_path / "notas.txt").is_file()
    assert not (tmp_path / "Imagens").exists()
    assert not (tmp_path / "Documentos").exists()
    assert not (tmp_path / HISTORY_FILE).exists()


def test_undo_only_reverts_the_last_run(tmp_path):
    make_files(tmp_path, "primeiro.png")
    apply_moves(tmp_path, plan_moves(tmp_path, EXTENSIONS))
    make_files(tmp_path, "segundo.png")
    apply_moves(tmp_path, plan_moves(tmp_path, EXTENSIONS))

    undo_last(tmp_path)

    assert (tmp_path / "segundo.png").is_file()
    assert (tmp_path / "Imagens" / "primeiro.png").is_file()
    history = json.loads((tmp_path / HISTORY_FILE).read_text(encoding="utf-8"))
    assert len(history) == 1


def test_undo_with_no_history_does_nothing(tmp_path):
    assert undo_last(tmp_path) == []


def test_build_extension_map_normalizes_extensions():
    mapping = build_extension_map({"Fotos": ["JPG", ".png", " heic "]})

    assert mapping == {".jpg": "Fotos", ".png": "Fotos", ".heic": "Fotos"}


def test_custom_config_is_loaded(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('[categorias]\nFaculdade = ["pdf", "docx"]\n', encoding="utf-8")

    assert load_extension_map(config) == {".pdf": "Faculdade", ".docx": "Faculdade"}


@pytest.mark.parametrize(
    "content",
    ["", "[categorias]\n", '[categorias]\nFotos = "jpg"\n', "isso não é toml ["],
)
def test_invalid_config_raises_config_error(tmp_path, content):
    config = tmp_path / "config.toml"
    config.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_extension_map(config)


def test_missing_config_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_extension_map(tmp_path / "nao-existe.toml")
