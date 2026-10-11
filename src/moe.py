"""Leakage-safe hybrid adaptive MoE with gradient gating and EW reliability."""
from __future__ import annotations
import numpy as np


class HybridAdaptiveMoE:
    def __init__(self, expert_names: list[str], alpha: float = 0.2, learning_rate: float = 0.01, epochs: int = 500):
        self.expert_names = expert_names
        self.alpha, self.learning_rate, self.epochs = alpha, learning_rate, epochs
        self.reliability = np.ones(len(expert_names), dtype=float)
        self.weights = None
        self.bias = None

    def fit_gating(self, context: np.ndarray, expert_predictions: np.ndarray, targets: np.ndarray) -> None:
        """Fit a linear softmax gate with gradient descent on historical calibration data."""
        x, forecasts, y = map(np.asarray, (context, expert_predictions, targets))
        self.weights = np.zeros((x.shape[1], len(self.expert_names)))
        self.bias = np.zeros(len(self.expert_names))
        for _ in range(self.epochs):
            logits = x @ self.weights + self.bias
            gate = np.exp(logits - logits.max(axis=1, keepdims=True)); gate /= gate.sum(axis=1, keepdims=True)
            prediction = (gate * forecasts).sum(axis=1)
            # d(MSE)/d(logit_j) through softmax and mixture prediction.
            gradient_logits = 2 * (prediction - y)[:, None] * gate * (forecasts - prediction[:, None]) / len(y)
            self.weights -= self.learning_rate * x.T @ gradient_logits
            self.bias -= self.learning_rate * gradient_logits.sum(axis=0)

    def predict(self, context: np.ndarray, expert_predictions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if self.weights is None:
            raise RuntimeError("Fit the gradient gate before inference")
        x, forecasts = map(np.asarray, (context, expert_predictions))
        logits = x @ self.weights + self.bias
        gate = np.exp(logits - logits.max(axis=1, keepdims=True)); gate /= gate.sum(axis=1, keepdims=True)
        adjusted = gate * self.reliability
        adjusted /= adjusted.sum(axis=1, keepdims=True)
        return (adjusted * forecasts).sum(axis=1), adjusted

    def observe(self, expert_predictions: np.ndarray, observed_value: float) -> None:
        """Call only after truth arrives; the result affects later predictions, never this one."""
        error = np.abs(np.asarray(expert_predictions, dtype=float) - observed_value)
        self.reliability = self.alpha * error + (1 - self.alpha) * self.reliability
        inverse = 1 / np.maximum(self.reliability, 1e-12)
        self.reliability = inverse / inverse.sum()
