from __future__ import annotations

from pathlib import Path
import pandas as pd


def read_la_trobe_chunks(path: Path, chunksize: int = 100_000):
    """Stream the large ZIP archive; do not materialize the whole source in memory."""
    for raw in pd.read_csv(path, compression="zip", chunksize=chunksize):
        required = {"campus_id", "meter_id", "timestamp", "consumption"}
        if not required.issubset(raw.columns):
            raise ValueError(f"La Trobe data must contain {sorted(required)}")
        timestamp = pd.to_datetime(raw["timestamp"], errors="coerce", utc=True)
        yield pd.DataFrame({
            "source_name": "la_trobe",
            "site_id": "campus_" + raw["campus_id"].astype(str),
            "asset_id": "meter_" + raw["campus_id"].astype(str) + "_" + raw["meter_id"].astype(str),
            "reading_time": timestamp,
            "energy_vector": "electricity",
            "consumption_value": raw["consumption"],
            "unit": "pending_validation",
            "interval_minutes": 15,
            "source_file": path.name,
            "source_row_number": raw.index + 2,
        })
