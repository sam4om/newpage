"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meridian-inducements",
        description="Consolidate Meridian IFA inducements CSVs into a MiFID II disclosure report.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing adviser_registry.csv, engagements.csv, claims.csv.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory where output CSVs will be written (created if missing).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    written = pipeline.run(args.input, args.output)
    for name, path in written.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
