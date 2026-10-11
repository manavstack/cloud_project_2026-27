from __future__ import annotations

from pathlib import Path
import pandas as pd


def read_iit_bombay(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"TS", "W1", "W2", "W3"}
    if not required.issubset(raw.columns):
        raise ValueError(f"{path} does not contain {sorted(required)}")
    timestamps = pd.to_datetime(raw["TS"], unit="s", errors="coerce", utc=True)
    phase_columns = ["W1", "W2", "W3"]
    phase_values = raw[phase_columns].apply(pd.to_numeric, errors="coerce")
    apartment = f"apartment_{path.stem}"
    return pd.DataFrame({
        "source_name": "iit_bombay",
        "site_id": "iit_bombay_residential",
        "asset_id": apartment,
        "reading_time": timestamps,
        "energy_vector": "electricity",
        "consumption_value": phase_values.sum(axis=1, min_count=len(phase_columns)),
        "unit": "Wh",
        "interval_minutes": 60,
        "source_file": path.name,
        "source_row_number": raw.index + 2,
    })
