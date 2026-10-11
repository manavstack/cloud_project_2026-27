"""Prediction-contract guards."""
from __future__ import annotations


def assert_aligned_predictions(predictions: list[dict]) -> None:
    if not predictions:
        raise ValueError("At least one expert prediction is required")
    fields = ("target_unit", "interval_minutes", "forecast_horizon")
    expected = {field: predictions[0][field] for field in fields}
    if any(any(prediction[field] != expected[field] for field in fields) for prediction in predictions[1:]):
        raise ValueError("Experts cannot be combined until unit, interval, and horizon align")
