"""
preprocessing.py
-----------------
Feature engineering for the Smart Campus short-term load forecasting model.

Reads the raw simulator output (dataset/raw/energy_readings_raw.csv), builds
time/lag/rolling features per building, and writes a model-ready dataset to
dataset/processed/energy_readings_features.csv.

Target: power_kw at t+1 step (next 15-minute reading), per building.
"""

import pandas as pd
import numpy as np

RAW_PATH = "dataset/raw/energy_readings_raw.csv"
PROCESSED_PATH = "dataset/processed/energy_readings_features.csv"

LAG_STEPS = [1, 4, 96]        # 15 min, 1 hour, 1 day (in 15-min steps)
ROLLING_WINDOWS = [4, 96]     # 1 hour, 1 day


def load_raw(path=RAW_PATH):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values(["building_id", "timestamp"]).reset_index(drop=True)
    return df


def add_time_features(df):
    ts = df["timestamp"]
    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek
    # cyclical encodings so the model sees hour 23 and hour 0 as close
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    return df


def add_lag_and_rolling_features(df):
    parts = []
    for building_id, g in df.groupby("building_id", sort=False):
        g = g.copy()
        for lag in LAG_STEPS:
            g[f"power_lag_{lag}"] = g["power_kw"].shift(lag)
        for window in ROLLING_WINDOWS:
            g[f"power_roll_mean_{window}"] = (
                g["power_kw"].shift(1).rolling(window=window, min_periods=1).mean()
            )
        # forecasting target: next reading's power
        g["target_power_kw"] = g["power_kw"].shift(-1)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def encode_categoricals(df):
    df = pd.get_dummies(df, columns=["building_id"], prefix="bldg")
    return df


def build_features(raw_path=RAW_PATH, processed_path=PROCESSED_PATH, save=True):
    df = load_raw(raw_path)
    df = add_time_features(df)
    df = add_lag_and_rolling_features(df)
    df = encode_categoricals(df)

    # drop rows with NaNs introduced by lag/shift at series boundaries
    df = df.dropna().reset_index(drop=True)

    if save:
        df.to_csv(processed_path, index=False)
        print(f"Saved processed feature set: {df.shape[0]:,} rows, "
              f"{df.shape[1]} columns -> {processed_path}")
    return df


if __name__ == "__main__":
    build_features()
