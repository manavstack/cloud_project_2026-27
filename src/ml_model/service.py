"""Database-backed chronological training, evaluation, and forecasting."""
from __future__ import annotations

import hashlib
import subprocess
from datetime import timedelta
from pathlib import Path
import re
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from psycopg.types.json import Jsonb
from sklearn.ensemble import HistGradientBoostingRegressor

from ..db import connect
from ..features import make_features
from ..train_experts import DEFAULT_FEATURES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models"
OBSERVATION_COLUMNS = [
    "source_name", "site_id", "asset_id", "reading_time",
    "energy_vector", "consumption_value", "unit", "interval_minutes",
]


def _safe_source(source: str) -> str:
    if not source or not re.fullmatch(r"[A-Za-z0-9_-]+", source):
        raise ValueError("Invalid source name")
    return source


def _parse_group_key(group_key: str) -> tuple[str, str, str, int]:
    try:
        source, vector, unit, raw_interval = group_key.split("|", 3)
        interval = int(raw_interval)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Select a dataset with a valid source, energy vector, unit, and cadence") from exc
    _safe_source(source)
    if vector not in {"electricity", "heat"} or not unit or interval <= 0:
        raise ValueError("Select a dataset with a valid source, energy vector, unit, and cadence")
    return source, vector, unit, interval


def _group_key(source: str, vector: str, unit: str, interval: int) -> str:
    return f"{source}|{vector}|{unit}|{interval}"


def _load_observations(group_key: str) -> pd.DataFrame:
    source, vector, unit, interval = _parse_group_key(group_key)
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT source_name, site_id, asset_id, reading_time, energy_vector,
                   consumption_value, unit, interval_minutes
            FROM energy_observations
            WHERE source_name = %s AND energy_vector = %s AND unit = %s
              AND interval_minutes = %s
            ORDER BY asset_id, reading_time
            """,
            (source, vector, unit, interval),
        )
        return pd.DataFrame(cursor.fetchall(), columns=OBSERVATION_COLUMNS)


def _model_path(group_key: str) -> Path:
    source, _, _, _ = _parse_group_key(group_key)
    key_hash = hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:16]
    return MODEL_DIR / f"{_safe_source(source)}-{key_hash}.joblib"


def _data_checksum(data: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(
            data[["asset_id", "reading_time", "consumption_value"]], index=False
        ).values.tobytes()
    ).hexdigest()


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = np.asarray(actual, dtype=float) - np.asarray(predicted, dtype=float)
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
    }


def dashboard_data(group_key: str | None = None) -> dict:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT source_name, energy_vector, unit, interval_minutes,
                   COUNT(*) AS observation_count, COUNT(DISTINCT asset_id) AS asset_count,
                   MIN(reading_time) AS first_reading, MAX(reading_time) AS last_reading,
                   AVG(consumption_value) AS mean_value,
                   MIN(consumption_value) AS min_value, MAX(consumption_value) AS max_value
            FROM energy_observations
            GROUP BY source_name, energy_vector, unit, interval_minutes
            ORDER BY source_name, energy_vector, unit, interval_minutes
            """
        )
        groups = cursor.fetchall()
        if not groups:
            raise ValueError("No observations found for the selected source")

        if group_key:
            expected_contract = _parse_group_key(group_key)
            selected_group = next(
                (row for row in groups if tuple(row[:4]) == expected_contract),
                None,
            )
            if selected_group is None:
                raise ValueError("No observations found for the selected dataset contract")
        else:
            selected_group = groups[0]
        selected_source = selected_group[0]
        vector, unit, interval = selected_group[1], selected_group[2], selected_group[3]
        cursor.execute(
            """
            SELECT source_name, asset_id, COUNT(*) AS observation_count,
                   MIN(reading_time) AS first_reading, MAX(reading_time) AS last_reading,
                   AVG(consumption_value) AS mean_value,
                   MIN(consumption_value) AS min_value, MAX(consumption_value) AS max_value
            FROM energy_observations
            WHERE source_name = %s AND energy_vector = %s AND unit = %s
              AND interval_minutes = %s
            GROUP BY source_name, asset_id
            ORDER BY source_name, asset_id
            """,
            (selected_source, vector, unit, interval),
        )
        assets = cursor.fetchall()
        cursor.execute(
            """
            SELECT (reading_time AT TIME ZONE 'UTC')::date AS day,
                   SUM(consumption_value) AS total_value,
                   AVG(consumption_value) AS mean_value,
                   COUNT(*) AS observations
            FROM energy_observations
            WHERE source_name = %s AND energy_vector = %s AND unit = %s
              AND interval_minutes = %s
            GROUP BY day ORDER BY day
            """,
            (selected_source, vector, unit, interval),
        )
        daily = cursor.fetchall()
        cursor.execute(
            """
            WITH ordered AS (
                SELECT reading_time,
                       LAG(reading_time) OVER (PARTITION BY asset_id ORDER BY reading_time) AS previous_time
                FROM energy_observations
                WHERE source_name = %s AND energy_vector = %s AND unit = %s
                  AND interval_minutes = %s
            )
            SELECT COUNT(*) FILTER (
                       WHERE previous_time IS NOT NULL
                         AND reading_time - previous_time != (%s * INTERVAL '1 minute')
                   ),
                   MAX(EXTRACT(EPOCH FROM (reading_time - previous_time)) / 3600)
            FROM ordered
            """,
            (selected_source, vector, unit, interval, interval),
        )
        gap_count, largest_gap_hours = cursor.fetchone()
        cursor.execute(
            """
            SELECT COUNT(*) FILTER (WHERE consumption_value = 0),
                   COUNT(*) FILTER (WHERE consumption_value < 0),
                   percentile_cont(0.95) WITHIN GROUP (ORDER BY consumption_value)
            FROM energy_observations
            WHERE source_name = %s AND energy_vector = %s AND unit = %s
              AND interval_minutes = %s
            """,
            (selected_source, vector, unit, interval),
        )
        zero_count, negative_count, percentile_95 = cursor.fetchone()

    def iso(value):
        return value.isoformat() if hasattr(value, "isoformat") else value

    def number(value):
        return float(value) if value is not None else None

    return {
        "sources": sorted({row[0] for row in groups}),
        "selected_source": selected_source,
        "selected_group_key": _group_key(selected_source, vector, unit, interval),
        "groups": [
            {
                "key": _group_key(row[0], row[1], row[2], row[3]),
                "label": f"{row[0]} · {row[1]} · {row[2]} · {row[3]} min",
                "source": row[0], "energy_vector": row[1], "unit": row[2],
                "interval_minutes": row[3], "observations": row[4], "assets": row[5],
                "first_reading": iso(row[6]), "last_reading": iso(row[7]),
                "mean": number(row[8]), "minimum": number(row[9]), "maximum": number(row[10]),
            }
            for row in groups
        ],
        "assets": [
            {
                "source": row[0], "asset_id": row[1], "observations": row[2],
                "first_reading": iso(row[3]), "last_reading": iso(row[4]),
                "mean": number(row[5]), "minimum": number(row[6]), "maximum": number(row[7]),
            }
            for row in assets
        ],
        "daily": [
            {"day": iso(row[0]), "total": number(row[1]), "mean": number(row[2]), "observations": row[3]}
            for row in daily
        ],
        "quality": {
            "zero_readings": zero_count,
            "negative_readings": negative_count,
            "p95": number(percentile_95),
            "off_cadence_transitions": gap_count,
            "largest_gap_hours": number(largest_gap_hours),
        },
    }


def model_status(group_key: str) -> dict:
    source, vector, unit, interval = _parse_group_key(group_key)
    path = _model_path(group_key)
    if not path.is_file():
        return {"trained": False, "source": source, "group_key": group_key}
    artifact = joblib.load(path)
    if artifact.get("group_key") != group_key:
        raise ValueError("Trained model does not match the selected dataset contract")
    current_checksum = _data_checksum(_load_observations(group_key))
    return {
        "trained": True,
        "source": source,
        "group_key": group_key,
        "energy_vector": vector,
        "unit": unit,
        "interval_minutes": interval,
        "experiment_id": artifact["experiment_id"],
        "cutoff": artifact["cutoff"],
        "train_observations": artifact["train_observations"],
        "test_observations": artifact["test_observations"],
        "metrics": artifact["metrics"],
        "baseline_metrics": artifact["baseline_metrics"],
        "unit": artifact["unit"],
        "model_beats_baseline": artifact["model_beats_baseline"],
        "data_is_current": current_checksum == artifact["data_checksum"],
    }


def train_model(group_key: str) -> dict:
    source, vector, unit, interval = _parse_group_key(group_key)
    data = _load_observations(group_key)
    if data.empty:
        raise ValueError(f"No observations are stored for source '{source}'")

    featured = make_features(data)
    usable = featured.dropna(subset=DEFAULT_FEATURES + ["consumption_value"]).copy()
    if len(usable) < 500:
        raise ValueError("At least 500 complete observations are required to train and evaluate")

    time_values = np.sort(usable["reading_time"].unique())
    cutoff = time_values[int(len(time_values) * 0.8)]
    train = usable[usable["reading_time"] < cutoff]
    test = usable[usable["reading_time"] >= cutoff]
    if len(train) < 100 or len(test) < 20:
        raise ValueError("Not enough observations on both sides of the chronological 80/20 split")

    model = HistGradientBoostingRegressor(
        max_iter=120,
        learning_rate=0.08,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=42,
    )
    model.fit(train[DEFAULT_FEATURES], train["consumption_value"])
    predicted = model.predict(test[DEFAULT_FEATURES])
    actual = test["consumption_value"].to_numpy(dtype=float)
    metrics = _metrics(actual, predicted)
    seasonal = test["lag_24"].to_numpy(dtype=float)
    baseline = _metrics(actual, seasonal)
    model_wins = metrics["mae"] < baseline["mae"]

    checksum = _data_checksum(data)
    experiment_id = uuid4()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    split_definition = {
        "strategy": "chronological",
        "train_fraction": 0.8,
        "cutoff": pd.Timestamp(cutoff).isoformat(),
        "test_observations": int(len(test)),
        "model_metrics": metrics,
        "seasonal_baseline_metrics": baseline,
    }
    feature_definition = {
        "source": source,
        "energy_vector": vector,
        "interval_minutes": interval,
        "features": DEFAULT_FEATURES,
        "estimator": "HistGradientBoostingRegressor",
        "max_iter": 120,
        "random_state": 42,
        "baseline": "24-observation seasonal persistence",
    }
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO experiment_runs
                (id, git_commit, data_checksum, split_definition, feature_definition, target_unit)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                experiment_id, commit, checksum, Jsonb(split_definition),
                Jsonb(feature_definition), unit,
            ),
        )
    artifact = {
        "model": model,
        "experiment_id": str(experiment_id),
        "group_key": group_key,
        "source": source,
        "energy_vector": vector,
        "unit": unit,
        "interval_minutes": interval,
        "features": DEFAULT_FEATURES,
        "metrics": metrics,
        "baseline_metrics": baseline,
        "train_observations": int(len(train)),
        "test_observations": int(len(test)),
        "cutoff": pd.Timestamp(cutoff).isoformat(),
        "data_checksum": checksum,
        "model_beats_baseline": model_wins,
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, _model_path(group_key))
    return {key: value for key, value in artifact.items() if key not in {"model"}}


def forecast(group_key: str, asset_id: str | None = None, horizon: int = 24) -> dict:
    source, vector, unit, interval = _parse_group_key(group_key)
    if not 1 <= int(horizon) <= 168:
        raise ValueError("Forecast horizon must be between 1 and 168 intervals")
    path = _model_path(group_key)
    if not path.is_file():
        raise FileNotFoundError(f"No trained model for '{source}, {vector}, {unit}'. Train the model from the dashboard first.")
    artifact = joblib.load(path)
    if (
        artifact.get("group_key") != group_key
        or artifact.get("energy_vector") != vector
        or artifact.get("unit") != unit
        or artifact.get("interval_minutes") != interval
    ):
        raise ValueError("Trained model does not match the selected dataset contract")
    observations = _load_observations(group_key)
    if _data_checksum(observations) != artifact["data_checksum"]:
        raise ValueError("Stored observations changed after training. Retrain the model before forecasting.")
    if asset_id is not None:
        observations = observations[observations["asset_id"] == asset_id]
    if observations.empty:
        raise ValueError(f"No observations found for the selected asset in '{source}'")

    asset = observations["asset_id"].iloc[0]
    history = observations[observations["asset_id"] == asset].sort_values("reading_time")
    if len(history) < 168:
        raise ValueError(f"Asset '{asset}' needs at least 168 readings to forecast")
    latest = pd.Timestamp(history["reading_time"].iloc[-1]).tz_convert("UTC")
    values = history["consumption_value"].to_numpy(dtype=float).tolist()
    predictions = []
    for step in range(1, int(horizon) + 1):
        timestamp = latest + timedelta(minutes=artifact["interval_minutes"] * step)
        hour = timestamp.hour
        weekday = timestamp.dayofweek
        context = {
            "hour": hour, "day_of_week": weekday, "month": timestamp.month,
            "is_weekend": int(weekday >= 5),
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "dow_sin": np.sin(2 * np.pi * weekday / 7),
            "dow_cos": np.cos(2 * np.pi * weekday / 7),
            "lag_1": values[-1], "lag_24": values[-24], "lag_168": values[-168],
        }
        prediction = float(artifact["model"].predict(pd.DataFrame([context], columns=artifact["features"]))[0])
        predictions.append({"time": timestamp.isoformat(), "value": prediction})
        values.append(prediction)

    return {
        "source": source, "group_key": group_key, "asset_id": asset, "unit": artifact["unit"],
        "energy_vector": artifact["energy_vector"], "interval_minutes": artifact["interval_minutes"],
        "horizon": int(horizon), "forecast_origin": latest.isoformat(), "model_metrics": artifact["metrics"],
        "baseline_metrics": artifact["baseline_metrics"], "predictions": predictions,
    }
