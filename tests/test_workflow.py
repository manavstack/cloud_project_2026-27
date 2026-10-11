import unittest
import numpy as np
import pandas as pd

from src.features import make_features
from src.moe import HybridAdaptiveMoE
from src.predict import assert_aligned_predictions


class WorkflowTests(unittest.TestCase):
    def test_lag_is_strictly_prior_observation(self):
        frame = pd.DataFrame({"asset_id": ["a", "a"], "reading_time": ["2026-01-01T00:00Z", "2026-01-01T01:00Z"], "consumption_value": [10, 20]})
        result = make_features(frame, lags=(1,))
        self.assertTrue(pd.isna(result.loc[0, "lag_1"]))
        self.assertEqual(result.loc[1, "lag_1"], 10)

    def test_reliability_changes_only_after_observation(self):
        model = HybridAdaptiveMoE(["a", "b"], epochs=1)
        model.fit_gating(np.array([[0.0], [1.0]]), np.array([[1.0, 2.0], [2.0, 3.0]]), np.array([1.0, 2.0]))
        before = model.reliability.copy()
        model.observe(np.array([1.0, 10.0]), 1.0)
        self.assertFalse(np.array_equal(before, model.reliability))
        self.assertGreater(model.reliability[0], model.reliability[1])

    def test_moe_requires_aligned_physical_contract(self):
        with self.assertRaises(ValueError):
            assert_aligned_predictions([
                {"target_unit": "kWh", "interval_minutes": 60, "forecast_horizon": 1},
                {"target_unit": "Wh", "interval_minutes": 60, "forecast_horizon": 1},
            ])
