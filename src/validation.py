"""Leakage and canonical-observation validation."""

from __future__ import annotations

import pandas as pd

CANONICAL_COLUMNS = [
    "source_name", "site_id", "asset_id", "reading_time", "energy_vector",
    "consumption_value", "unit", "interval_minutes", "source_file", "source_row_number",
]


def validate_observations(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(CANONICAL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing canonical columns: {sorted(missing)}")
    data = frame[CANONICAL_COLUMNS].copy()
    data["reading_time"] = pd.to_datetime(data["reading_time"], utc=True, errors="coerce")
    data["consumption_value"] = pd.to_numeric(data["consumption_value"], errors="coerce")
    invalid = data["reading_time"].isna() | data["consumption_value"].isna()
    if invalid.any():
        raise ValueError(f"Found {int(invalid.sum())} malformed timestamp or target rows")
    key = ["source_name", "site_id", "asset_id", "reading_time", "energy_vector"]
    if data.duplicated(key).any():
        raise ValueError("Duplicate source/asset/time/energy-vector keys detected")
    if not data["energy_vector"].isin(["electricity", "heat"]).all():
        raise ValueError("energy_vector must be electricity or heat")
    return data.sort_values(key).reset_index(drop=True)
