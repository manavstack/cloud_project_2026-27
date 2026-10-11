from __future__ import annotations
import numpy as np


def regression_metrics(actual, predicted) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return {"mae": float(np.mean(np.abs(actual - predicted))), "rmse": float(np.sqrt(np.mean((actual - predicted) ** 2)))}
