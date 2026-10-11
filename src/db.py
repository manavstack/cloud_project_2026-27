"""PostgreSQL connection and migration helpers for Feature 1."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import database_dsn


def connect():
    """Open a PostgreSQL connection to the configured cloud_project database."""
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc
    return psycopg.connect(database_dsn())


def apply_migrations() -> None:
    """Apply local SQL migrations in filename order within individual transactions."""
    migrations = Path(__file__).resolve().parents[1] / "database" / "migrations"
    with connect() as connection:
        with connection.cursor() as cursor:
            for migration in sorted(migrations.glob("*.sql")):
                cursor.execute(migration.read_text(encoding="utf-8"))


def store_observations(frame: pd.DataFrame, batch_size: int = 10_000) -> int:
    """Upsert validated canonical observations in bounded batches."""
    fields = [
        "source_name", "site_id", "asset_id", "reading_time", "energy_vector",
        "consumption_value", "unit", "interval_minutes", "source_file", "source_row_number",
    ]
    rows = frame[fields].itertuples(index=False, name=None)
    statement = """
        INSERT INTO energy_observations
        (source_name, site_id, asset_id, reading_time, energy_vector, consumption_value,
         unit, interval_minutes, source_file, source_row_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_name, site_id, asset_id, reading_time, energy_vector)
        DO UPDATE SET consumption_value = EXCLUDED.consumption_value,
                      unit = EXCLUDED.unit,
                      interval_minutes = EXCLUDED.interval_minutes,
                      source_file = EXCLUDED.source_file,
                      source_row_number = EXCLUDED.source_row_number,
                      ingested_at = CURRENT_TIMESTAMP
    """
    total, batch = 0, []
    with connect() as connection:
        with connection.cursor() as cursor:
            for row in rows:
                batch.append(row)
                if len(batch) == batch_size:
                    cursor.executemany(statement, batch)
                    total += len(batch)
                    batch.clear()
            if batch:
                cursor.executemany(statement, batch)
                total += len(batch)
    return total
