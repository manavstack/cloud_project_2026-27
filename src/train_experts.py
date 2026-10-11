from __future__ import annotations
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

DEFAULT_FEATURES = ["hour", "day_of_week", "month", "is_weekend", "hour_sin", "hour_cos", "dow_sin", "dow_cos", "lag_1", "lag_24", "lag_168"]


def train_source_experts(data: pd.DataFrame, features: list[str] = DEFAULT_FEATURES):
    experts = {}
    for source, partition in data.dropna(subset=features).groupby("source_name"):
        model = GradientBoostingRegressor(random_state=42)
        model.fit(partition[features], partition["consumption_value"])
        experts[source] = model
    return experts
