"""
predict.py
----------
Loads the trained model and produces a next-step power forecast for a given
building's latest reading window. This is the piece that would be called by
(or packaged into) the SageMaker endpoint / model-loading Lambda described in
the Buildable MVP Plan, and consumed by the control-policy Lambda that
compares forecast vs. tariff windows every 15 minutes.

Usage (standalone):
    python3 src/ml_model/predict.py

As a library:
    from predict import load_model, predict_next
"""

import json
import joblib
import pandas as pd

from preprocessing import add_time_features, add_lag_and_rolling_features, encode_categoricals

MODEL_PATH = "src/ml_model/model.pkl"
FEATURE_COLS_PATH = "src/ml_model/feature_columns.json"


def load_model(model_path=MODEL_PATH, feature_cols_path=FEATURE_COLS_PATH):
    model = joblib.load(model_path)
    with open(feature_cols_path) as f:
        feature_cols = json.load(f)
    return model, feature_cols


def predict_next(model, feature_cols, recent_readings: pd.DataFrame):
    """
    recent_readings: DataFrame of the most recent readings for ONE building,
    sorted by timestamp ascending, with at least 96+1 rows so lag/rolling
    features can be computed. Columns must match the raw simulator schema:
    building_id, timestamp, power_kw, occupancy, temperature_c,
    humidity_pct, is_weekend.

    Returns: predicted power_kw for the next 15-minute step.
    """
    df = recent_readings.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = add_time_features(df)
    df = add_lag_and_rolling_features(df)
    df = encode_categoricals(df)

    # align columns with training-time feature set (missing building dummies -> 0)
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_cols]

    latest_row = df.iloc[[-1]]  # lag/rolling features are backward-looking, so
                                 # the most recent row already has everything it needs
    prediction = model.predict(latest_row)[0]
    return round(float(prediction), 3)


def demo():
    """Quick sanity-check demo using the tail of the processed dataset."""
    model, feature_cols = load_model()
    raw = pd.read_csv("dataset/raw/energy_readings_raw.csv")
    sample = raw[raw["building_id"] == "B01_ACADEMIC"].tail(120)
    forecast = predict_next(model, feature_cols, sample)
    print(f"Forecasted next-step load for B01_ACADEMIC: {forecast} kW")


if __name__ == "__main__":
    demo()
