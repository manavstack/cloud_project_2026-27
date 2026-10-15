"""
moe.py
======
Mixture of Experts (MoE) Gating Layer for FEDRA.
Combines predictions from Academic, Residential, and Others experts
using assigned or calibrated contribution weights:

    ŷ_final = wA * ŷA + wR * ŷR + wO * ŷO

where wA + wR + wO = 1.0
"""

from typing import Dict, Optional, Tuple


class MixtureOfExperts:
    """
    Gating mechanism to combine individual category expert predictions.
    """

    DEFAULT_EQUAL_WEIGHTS = {
        "academic": 1.0 / 3.0,
        "residential": 1.0 / 3.0,
        "others": 1.0 / 3.0,
    }

    CATEGORY_PRIORS = {
        "academic": {"academic": 0.80, "residential": 0.10, "others": 0.10},
        "residential": {"academic": 0.10, "residential": 0.80, "others": 0.10},
        "others": {"academic": 0.10, "residential": 0.10, "others": 0.80},
    }

    @staticmethod
    def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
        """Ensure all weights sum strictly to 1.0."""
        total = sum(weights.values())
        if total <= 0:
            return MixtureOfExperts.DEFAULT_EQUAL_WEIGHTS.copy()
        return {k: v / total for k, v in weights.items()}

    @classmethod
    def combine(
        cls,
        expert_predictions: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> Tuple[float, Dict[str, float], Dict[str, float]]:
        """
        Calculates the weighted MoE final prediction.

        Returns:
            final_prediction (float): Weighted sum of expert predictions.
            normalized_weights (dict): The normalized influence weight for each expert.
            contributions (dict): The exact kWh contribution of each expert (w_i * ŷ_i).
        """
        if weights is None:
            norm_weights = cls.DEFAULT_EQUAL_WEIGHTS.copy()
        else:
            norm_weights = cls.normalize_weights(weights)

        contributions = {}
        final_prediction = 0.0

        for category, pred in expert_predictions.items():
            w = norm_weights.get(category, 0.0)
            contrib = w * pred
            contributions[category] = contrib
            final_prediction += contrib

        return final_prediction, norm_weights, contributions
