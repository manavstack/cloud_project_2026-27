import unittest

import numpy as np
import pandas as pd

from src.federated.train import (
    FEATURE_NAMES,
    _fedavg,
    _prepare_client,
    _temporal_features,
    _fit_local,
)


class FederatedTrainingTests(unittest.TestCase):
    def test_fedavg_weights_updates_by_training_observations(self):
        averaged = _fedavg(
            [
                (np.array([1.0, 3.0]), 1),
                (np.array([5.0, 7.0]), 3),
            ]
        )
        np.testing.assert_allclose(averaged, [4.0, 6.0])

    def test_fedavg_rejects_incompatible_client_weights(self):
        with self.assertRaisesRegex(ValueError, "matching model shapes"):
            _fedavg([(np.zeros(2), 1), (np.zeros(3), 1)])

    def test_temporal_features_use_campus_local_clock(self):
        timestamps = pd.Series(pd.to_datetime(["2024-01-01T00:00:00Z"], utc=True))
        features = _temporal_features(timestamps, "Asia/Kolkata")
        self.assertAlmostEqual(features[0, 0], np.sin(2 * np.pi * 5.5 / 24))
        self.assertAlmostEqual(features[0, 1], np.cos(2 * np.pi * 5.5 / 24))
        self.assertAlmostEqual(features[0, 2], 0.0)

    def test_client_uses_later_rows_for_chronological_evaluation(self):
        times = pd.date_range("2024-01-01", periods=600, freq="h", tz="UTC")
        frame = pd.DataFrame(
            {"reading_time": times, "consumption_value": np.arange(1.0, 601.0)}
        )
        client, excluded = _prepare_client(
            "campus_a", "test_source", "sample.csv", "kWh", "UTC", frame
        )
        self.assertIsNotNone(client)
        self.assertEqual(excluded, {})
        self.assertEqual(len(client.x_train), 480)
        self.assertEqual(len(client.x_test), 120)
        self.assertEqual(client.cutoff, times[480].isoformat())
        self.assertEqual(client.x_train.shape[1], len(FEATURE_NAMES))
        self.assertGreater(client.scale, 0)

    def test_short_client_is_reported_as_excluded(self):
        times = pd.date_range("2024-01-01", periods=30, freq="h", tz="UTC")
        frame = pd.DataFrame({"reading_time": times, "consumption_value": 1.0})
        client, status = _prepare_client(
            "campus_a", "test_source", "short.csv", "kWh", "UTC", frame
        )
        self.assertIsNone(client)
        self.assertEqual(status["status"], "excluded")
        self.assertIn("at least 500", status["reason"])

    def test_local_training_updates_initial_weights(self):
        times = pd.date_range("2024-01-01", periods=600, freq="h", tz="UTC")
        values = 2 + np.sin(2 * np.pi * times.hour / 24)
        client, _ = _prepare_client(
            "campus_a",
            "test_source",
            "sample.csv",
            "kWh",
            "UTC",
            pd.DataFrame({"reading_time": times, "consumption_value": values}),
        )
        initial = np.zeros(len(FEATURE_NAMES))
        trained = _fit_local(initial, client, epochs=10, learning_rate=0.03)
        self.assertFalse(np.array_equal(initial, trained))


if __name__ == "__main__":
    unittest.main()
