"""Train client-local campus profiles and aggregate them with FedAvg."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from zipfile import BadZipFile

import numpy as np
import pandas as pd

from ..ingest.iit_bombay import read_iit_bombay
from ..ingest.valahia import read_valahia

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "cloud datasets AWS uni"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "federated_demo" / "weights.json"
FEATURE_NAMES = ("hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "bias")
MIN_OBSERVATIONS = 500
LOCAL_EPOCHS = 20
DEFAULT_ROUNDS = 5
LEARNING_RATE = 0.03
IIITD_BUILDING_FILES = (
    "acad_build_mains.csv.zip",
    "boys_hostel_mains.csv",
    "boys_hostel_ups.csv.zip",
    "facilities_build_mains.csv.zip",
    "girls_hostel_mains.csv",
    "girls_hostel_ups.csv.zip",
    "lecture_build_mains.csv",
    "library_build_mains.csv.zip",
    "mess_build_mains.csv.zip",
)


@dataclass(frozen=True)
class ClientData:
    client_id: str
    source: str
    dataset: str
    unit: str
    timezone: str
    observations: int
    source_rows: int
    excluded_observations: int
    scale: float
    cutoff: str
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray


def _temporal_features(reading_time: pd.Series, timezone: str) -> np.ndarray:
    timestamps = pd.to_datetime(reading_time, utc=True, errors="coerce").dt.tz_convert(timezone)
    hour = timestamps.dt.hour + timestamps.dt.minute / 60
    weekday = timestamps.dt.dayofweek
    return np.column_stack(
        (
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
            np.sin(2 * np.pi * weekday / 7),
            np.cos(2 * np.pi * weekday / 7),
            np.ones(len(timestamps)),
        )
    )


def _prepare_client(
    client_id: str,
    source: str,
    dataset: str,
    unit: str,
    timezone: str,
    frame: pd.DataFrame,
) -> tuple[ClientData | None, dict]:
    required = {"reading_time", "consumption_value"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{dataset} is missing required columns: {sorted(required - set(frame.columns))}")

    timestamps = pd.to_datetime(frame["reading_time"], utc=True, errors="coerce")
    values = pd.to_numeric(frame["consumption_value"], errors="coerce")
    valid = timestamps.notna() & values.notna() & np.isfinite(values)
    usable = pd.DataFrame({"reading_time": timestamps[valid], "value": values[valid]})
    usable = usable.sort_values("reading_time", kind="stable")
    excluded = int(len(frame) - len(usable))
    if len(usable) < MIN_OBSERVATIONS:
        return None, {
            "client_id": client_id,
            "source": source,
            "dataset": dataset,
            "status": "excluded",
            "observations": int(len(usable)),
            "excluded_observations": excluded,
            "reason": f"Needs at least {MIN_OBSERVATIONS} valid timestamp/value rows",
        }

    split = int(len(usable) * 0.8)
    if split < 2 or len(usable) - split < 20:
        return None, {
            "client_id": client_id,
            "source": source,
            "dataset": dataset,
            "status": "excluded",
            "observations": int(len(usable)),
            "excluded_observations": excluded,
            "reason": "Not enough observations on both sides of the chronological holdout",
        }

    train_values = usable["value"].to_numpy(dtype=np.float64)[:split]
    scale = float(np.mean(np.abs(train_values)))
    if not np.isfinite(scale) or scale <= 0:
        return None, {
            "client_id": client_id,
            "source": source,
            "dataset": dataset,
            "status": "excluded",
            "observations": int(len(usable)),
            "excluded_observations": excluded,
            "reason": "Training observations do not define a positive normalization scale",
        }

    features = _temporal_features(usable["reading_time"], timezone)
    target = usable["value"].to_numpy(dtype=np.float64) / scale
    return ClientData(
        client_id=client_id,
        source=source,
        dataset=dataset,
        unit=unit,
        timezone=timezone,
        observations=int(len(usable)),
        source_rows=int(len(frame)),
        excluded_observations=excluded,
        scale=scale,
        cutoff=usable["reading_time"].iloc[split].isoformat(),
        x_train=features[:split],
        y_train=target[:split],
        x_test=features[split:],
        y_test=target[split:],
    ), {}


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = np.asarray(actual, dtype=np.float64) - np.asarray(predicted, dtype=np.float64)
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
    }


def _fedavg(updates: list[tuple[np.ndarray, int]]) -> np.ndarray:
    if not updates:
        raise ValueError("FedAvg requires at least one client update")
    total_examples = sum(count for _, count in updates)
    if total_examples <= 0 or any(count <= 0 for _, count in updates):
        raise ValueError("FedAvg client weights must be positive")
    shape = updates[0][0].shape
    if any(weights.shape != shape for weights, _ in updates):
        raise ValueError("FedAvg client updates must have matching model shapes")
    return sum(weights * count for weights, count in updates) / total_examples


def _fit_local(
    initial_weights: np.ndarray,
    client: ClientData,
    epochs: int,
    learning_rate: float,
) -> np.ndarray:
    weights = initial_weights.copy()
    for _ in range(epochs):
        error = client.x_train @ weights - client.y_train
        gradient = (2.0 / len(client.y_train)) * (client.x_train.T @ error)
        weights -= learning_rate * gradient
    return weights


def _evaluate(client: ClientData, weights: np.ndarray) -> dict:
    predicted = np.maximum(client.x_test @ weights, 0)
    actual = client.y_test
    baseline = np.full_like(actual, float(np.mean(client.y_train)))
    return {
        "normalized_mae": _metrics(actual, predicted)["mae"],
        "normalized_rmse": _metrics(actual, predicted)["rmse"],
        "normalized_baseline_mae": _metrics(actual, baseline)["mae"],
        "test_observations": int(len(client.y_test)),
    }


def _read_iiitd_hourly(path: Path, chunksize: int = 100_000) -> tuple[pd.DataFrame, int, int]:
    hourly: dict[pd.Timestamp, list[float]] = {}
    raw_rows = 0
    valid_rows = 0
    try:
        chunks = pd.read_csv(path, compression="zip" if path.suffix == ".zip" else None, chunksize=chunksize)
        for chunk in chunks:
            if not {"timestamp", "power"}.issubset(chunk.columns):
                raise ValueError(f"{path} must contain timestamp and power columns")
            raw_rows += len(chunk)
            timestamps = pd.to_datetime(chunk["timestamp"], unit="s", errors="coerce", utc=True)
            power = pd.to_numeric(chunk["power"], errors="coerce")
            valid = timestamps.notna() & power.notna() & np.isfinite(power)
            valid_rows += int(valid.sum())
            local_hours = timestamps[valid].dt.tz_convert("Asia/Kolkata").dt.floor("h")
            grouped = pd.DataFrame(
                {"hour": local_hours, "power": power[valid].to_numpy(dtype=np.float64)}
            ).groupby("hour")["power"].agg(["sum", "count"])
            for hour, row in grouped.iterrows():
                totals = hourly.setdefault(pd.Timestamp(hour), [0.0, 0.0])
                totals[0] += float(row["sum"])
                totals[1] += int(row["count"])
    except BadZipFile as exc:
        raise ValueError(f"Could not read campus archive {path}") from exc

    frame = pd.DataFrame(
        {
            "reading_time": list(hourly),
            "consumption_value": [
                total / count for total, count in hourly.values()
            ],
        }
    )
    return frame, raw_rows, valid_rows


def _load_clients(data_root: Path) -> tuple[list[ClientData], list[dict]]:
    clients: list[ClientData] = []
    excluded: list[dict] = []

    iit_root = data_root / "IIT-B - H"
    for path in sorted(iit_root.glob("[0-9]*.csv"), key=lambda item: int(item.stem)):
        frame = read_iit_bombay(path)
        client, status = _prepare_client(
            f"iit_bombay_apartment_{path.stem}",
            "iit_bombay",
            path.name,
            "Wh",
            "Asia/Kolkata",
            frame,
        )
        if client:
            clients.append(client)
        else:
            excluded.append(status)

    iiitd_root = data_root / "IIIT-D - AHO" / "energy_dataset"
    for filename in IIITD_BUILDING_FILES:
        path = iiitd_root / filename
        if not path.is_file():
            continue
        frame, raw_rows, valid_rows = _read_iiitd_hourly(path)
        client, status = _prepare_client(
            f"iiit_delhi_{path.name.removesuffix('.csv.zip').removesuffix('.csv')}",
            "iiit_delhi",
            path.name,
            "W",
            "Asia/Kolkata",
            frame,
        )
        if client:
            clients.append(
                ClientData(
                    client_id=client.client_id,
                    source=client.source,
                    dataset=client.dataset,
                    unit=client.unit,
                    timezone=client.timezone,
                    observations=client.observations,
                    source_rows=raw_rows,
                    excluded_observations=raw_rows - valid_rows,
                    scale=client.scale,
                    cutoff=client.cutoff,
                    x_train=client.x_train,
                    y_train=client.y_train,
                    x_test=client.x_test,
                    y_test=client.y_test,
                )
            )
        else:
            status["source_rows"] = raw_rows
            status["excluded_observations"] = raw_rows - valid_rows
            excluded.append(status)

    valahia_root = data_root / "valahia uni of targoviste - O" / "UVTgv_OD" / "demand"
    for path in sorted(valahia_root.glob("UVTgv_*_demand_building_*.csv")):
        frame = read_valahia(path)
        client, status = _prepare_client(
            f"valahia_{path.stem}",
            "valahia_uvtgv",
            path.name,
            "kWh",
            "Europe/Bucharest",
            frame,
        )
        if client:
            clients.append(client)
        else:
            excluded.append(status)

    twente_root = data_root / "uni of twente - AHO"
    for path in sorted(twente_root.glob("*.csv")):
        frame = pd.read_csv(path)
        count = int(len(frame))
        excluded.append(
            {
                "client_id": f"twente_{path.stem}",
                "source": "university_of_twente",
                "dataset": path.name,
                "status": "excluded",
                "observations": count,
                "excluded_observations": 0,
                "reason": (
                    f"Only {count} rows; at least {MIN_OBSERVATIONS} valid rows are required "
                    "for a chronological local holdout"
                ),
            }
        )

    la_trobe = data_root / "la trobe uni - H" / "building_consumption.csv.zip"
    if la_trobe.is_file():
        excluded.append(
            {
                "client_id": "la_trobe_campus_meters",
                "source": "la_trobe",
                "dataset": la_trobe.name,
                "status": "excluded",
                "observations": None,
                "excluded_observations": None,
                "reason": "Source unit and timezone are pending validation; no local-time profile is inferred",
            }
        )
    return clients, excluded


def train_federated(
    data_root: Path = DATA_ROOT,
    rounds: int = DEFAULT_ROUNDS,
    local_epochs: int = LOCAL_EPOCHS,
    learning_rate: float = LEARNING_RATE,
) -> dict:
    if rounds < 1 or local_epochs < 1 or learning_rate <= 0:
        raise ValueError("Rounds, local epochs, and learning rate must be positive")
    clients, excluded = _load_clients(data_root)
    if not clients:
        raise ValueError(f"No eligible campus datasets were found under {data_root}")

    weights = np.zeros(len(FEATURE_NAMES), dtype=np.float64)
    local_weights: dict[str, np.ndarray] = {}
    round_history = []
    for round_number in range(1, rounds + 1):
        updates = []
        for client in clients:
            local_weights[client.client_id] = _fit_local(
                weights, client, local_epochs, learning_rate
            )
            updates.append((local_weights[client.client_id], len(client.y_train)))
        weights = _fedavg(updates)
        round_history.append(
            {
                "round": round_number,
                "participating_clients": len(updates),
                "training_observations": sum(count for _, count in updates),
                "global_weights": weights.tolist(),
            }
        )

    participants = []
    for client in clients:
        client_weights = local_weights[client.client_id]
        participants.append(
            {
                "client_id": client.client_id,
                "source": client.source,
                "dataset": client.dataset,
                "target_unit": client.unit,
                "local_timezone": client.timezone,
                "observations": client.observations,
                "source_rows": client.source_rows,
                "excluded_observations": client.excluded_observations,
                "train_observations": int(len(client.y_train)),
                "test_observations": int(len(client.y_test)),
                "chronological_cutoff": client.cutoff,
                "metrics": _evaluate(client, client_weights),
            }
        )
    return {
        "schema_version": 1,
        "model": "federated_normalized_campus_profile_linear_v1",
        "interpretation": (
            "The global model predicts client-local mean-normalized demand from local hour "
            "and weekday. Each campus retains its private normalization scale and raw records. "
            "Client update vectors are not written to the shared artifact."
        ),
        "federation_mode": "single-machine FedAvg simulation; no campus network or secure aggregation",
        "training": {
            "algorithm": "FedAvg",
            "rounds": rounds,
            "local_epochs_per_round": local_epochs,
            "learning_rate": learning_rate,
            "minimum_client_observations": MIN_OBSERVATIONS,
            "chronological_train_fraction": 0.8,
            "features": list(FEATURE_NAMES),
            "aggregation_weight": "number of local training observations",
            "input_data_location": (
                data_root.resolve().relative_to(PROJECT_ROOT).as_posix()
                if data_root.resolve().is_relative_to(PROJECT_ROOT)
                else "external local path"
            ),
            "raw_records_transferred": False,
        },
        "global_weights": weights.tolist(),
        "global_weight_names": list(FEATURE_NAMES),
        "round_history": round_history,
        "participants": participants,
        "excluded_datasets": excluded,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    args = parser.parse_args()
    result = train_federated(args.data_root, rounds=args.rounds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        f"Trained {len(result['participants'])} local clients over {args.rounds} FedAvg rounds. "
        f"Excluded {len(result['excluded_datasets'])} datasets; transferred weights saved to {args.output}"
    )


if __name__ == "__main__":
    main()
