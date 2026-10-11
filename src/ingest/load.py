"""CLI to validate and load one source at a time into PostgreSQL."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..db import apply_migrations, store_observations
from ..validation import validate_observations
from .iit_bombay import read_iit_bombay
from .la_trobe import read_la_trobe_chunks
from .valahia import read_valahia


def load_iit(directory: Path) -> int:
    return sum(store_observations(validate_observations(read_iit_bombay(path))) for path in sorted(directory.glob("*.csv")))


def load_valahia(directory: Path) -> int:
    return sum(store_observations(validate_observations(read_valahia(path))) for path in sorted(directory.glob("UVTgv_*_demand_building_*.csv")))


def load_la_trobe(archive: Path) -> int:
    return sum(store_observations(validate_observations(chunk)) for chunk in read_la_trobe_chunks(archive))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=("iit", "la-trobe", "valahia"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    apply_migrations()
    loaders = {"iit": load_iit, "la-trobe": load_la_trobe, "valahia": load_valahia}
    print(f"Stored {loaders[args.source](args.path)} observations.")


if __name__ == "__main__":
    main()
