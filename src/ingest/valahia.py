from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

_NAME = re.compile(r"UVTgv_(elec|heat)_demand_building_([A-Z]+)_(20\d{2})\.csv$")


def read_valahia(path: Path) -> pd.DataFrame:
    match = _NAME.match(path.name)
    if not match:
        raise ValueError(f"Unexpected Valahia filename: {path.name}")
    kind, building, year = match.groups()
    raw = pd.read_csv(path)
    if list(raw.columns) != ["kWh"]:
        raise ValueError(f"{path} must contain only a kWh column")
    # Hourly sequence is reconstructed from documented year; timezone is recorded as Europe/Bucharest.
    timestamps = pd.date_range(f"{year}-01-01", periods=len(raw), freq="h", tz="Europe/Bucharest")
    return pd.DataFrame({
        "source_name": "valahia_uvtgv",
        "site_id": "uvtgv",
        "asset_id": building,
        "reading_time": timestamps.tz_convert("UTC"),
        "energy_vector": "electricity" if kind == "elec" else "heat",
        "consumption_value": raw["kWh"],
        "unit": "kWh",
        "interval_minutes": 60,
        "source_file": path.name,
        "source_row_number": raw.index + 2,
    })
