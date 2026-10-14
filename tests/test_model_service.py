import unittest

import numpy as np

from src.ml_model.service import _metrics, _safe_source


class ModelServiceTests(unittest.TestCase):
    def test_metrics_report_mae_and_rmse(self):
        self.assertEqual(
            _metrics(np.array([1.0, 3.0]), np.array([2.0, 1.0])),
            {"mae": 1.5, "rmse": float(np.sqrt(2.5))},
        )

    def test_source_name_rejects_path_separators(self):
        with self.assertRaisesRegex(ValueError, "Invalid source"):
            _safe_source("../outside")


if __name__ == "__main__":
    unittest.main()
