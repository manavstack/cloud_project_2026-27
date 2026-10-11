"""Leakage-safe, time-derived forecasting features."""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_features(frame: pd.DataFrame, lags: tuple[int, ...] = (1, 24, 168)) -> pd.DataFrame:
    data = frame.sort_values(["asset_id", "reading_time"]).copy()
    timestamp = pd.to_datetime(data["reading_time"], utc=True)
    data["hour"] = timestamp.dt.hour
    data["day_of_week"] = timestamp.dt.dayofweek
    data["month"] = timestamp.dt.month
    data["is_weekend"] = (timestamp.dt.dayofweek >= 5).astype(int)
    data["hour_sin"] = np.sin(2 * np.pi * data["hour"] / 24)
    data["hour_cos"] = np.cos(2 * np.pi * data["hour"] / 24)
    data["dow_sin"] = np.sin(2 * np.pi * data["day_of_week"] / 7)
    data["dow_cos"] = np.cos(2 * np.pi * data["day_of_week"] / 7)
    grouped = data.groupby("asset_id", sort=False)["consumption_value"]
    for lag in lags:
        data[f"lag_{lag}"] = grouped.shift(lag)  # strictly earlier observations only
    return data
