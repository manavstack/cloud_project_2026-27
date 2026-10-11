from __future__ import annotations
import pandas as pd
from .evaluation import regression_metrics


def chronological_split(data: pd.DataFrame, test_fraction: float = 0.2):
    ordered = data.sort_values("reading_time")
    boundary = int(len(ordered) * (1 - test_fraction))
    return ordered.iloc[:boundary].copy(), ordered.iloc[boundary:].copy()


def evaluate_persistence(data: pd.DataFrame, seasonal_lag: int = 24) -> dict[str, float]:
    ordered = data.sort_values(["asset_id", "reading_time"]).copy()
    ordered["forecast"] = ordered.groupby("asset_id")["consumption_value"].shift(seasonal_lag)
    test = ordered.dropna(subset=["forecast"])
    return regression_metrics(test["consumption_value"], test["forecast"])
