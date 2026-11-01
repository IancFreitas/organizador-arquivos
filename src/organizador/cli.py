"""Interface de linha de comando do organizador."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

from organizador.config import ConfigError, load_extension_map
from organizador.organizer import Move, apply_moves, plan_moves, undo_last

logger = logging.getLogger("organizador")

# No modo monitorar, espera o arquivo ficar alguns segundos sem mudanças antes de movê-lo.
WATCH_MIN_FILE_AGE_SECONDS = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="organizador",
        description="Organiza automaticamente os arquivos de uma pasta em subpastas por tipo.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="mostra mensagens de depuração")
    subparsers = parser.add_subparsers(dest="command", required=True)

    organize = subparsers.add_parser("organizar", help="organiza os arquivos da pasta")
    organize.add_argument("pasta", type=Path, help="pasta a ser organizada (ex.: ~/Downloads)")
    organize.add_argument(
        "--simular", action="store_true", help="só mostra o que seria feito, sem mover nada"
    )
    organize.add_argument(
        "--por-data", action="store_true", help="cria subpastas AAAA-MM dentro de cada categoria"
    )
    organize.add_argument("--config", type=Path, help="arquivo TOML com categorias personalizadas")
    organize.add_argument(
        "--monitorar", action="store_true", help="continua rodando e organiza novos arquivos"
    )
    organize.add_argument(
        "--intervalo",
        type=float,
        default=10,
        help="segundos entre verificações no modo monitorar (padrão: 10)",
    )

    undo = subparsers.add_parser("desfazer", help="desfaz a última organização da pasta")
    undo.add_argument("pasta", type=Path, help="pasta que foi organizada")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    folder: Path = args.pasta.expanduser().resolve()
    if not folder.is_dir():
        logger.error("Pasta não encontrada: %s", folder)
        return 1

    if args.command == "desfazer":
        restored = undo_last(folder)
        if restored:
            logger.info("%d arquivo(s) restaurado(s).", len(restored))
        else:
            logger.info("Nada para desfazer em %s.", folder)
        return 0

    try:
        extension_map = load_extension_map(args.config)
    except ConfigError as error:
        logger.error("%s", error)
        return 1

    if args.monitorar:
        if args.simular:
            logger.error("--simular não pode ser usado junto com --monitorar.")
            return 1
        _watch(folder, extension_map, args.por_data, args.intervalo)
        return 0

    moves = plan_moves(folder, extension_map, by_date=args.por_data)
    if not moves:
        logger.info("Nenhum arquivo para organizar em %s.", folder)
        return 0

    if args.simular:
        for move in moves:
            print(f"[simulação] {move.source.name} -> {move.destination.relative_to(folder)}")
    else:
        apply_moves(folder, moves)

    _print_summary(folder, moves, simulated=args.simular)
    return 0


def _watch(folder: Path, extension_map: dict[str, str], by_date: bool, interval: float) -> None:
    logger.info("Monitorando %s a cada %ss (Ctrl+C para parar).", folder, interval)
    try:
        while True:
            moves = plan_moves(
                folder, extension_map, by_date=by_date, min_age_seconds=WATCH_MIN_FILE_AGE_SECONDS
            )
            if moves:
                apply_moves(folder, moves)
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Monitoramento encerrado.")


def _print_summary(folder: Path, moves: list[Move], *, simulated: bool) -> None:
    per_category = Counter(move.destination.relative_to(folder).parts[0] for move in moves)
    verb = "seriam movidos" if simulated else "movidos"
    print(f"\n{len(moves)} arquivo(s) {verb}:")
    for category, count in per_category.most_common():
        print(f"  {category:<15} {count}")


if __name__ == "__main__":
    sys.exit(main())
