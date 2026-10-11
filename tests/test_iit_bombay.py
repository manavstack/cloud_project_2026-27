import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.ingest.iit_bombay import read_iit_bombay
from src.validation import validate_observations


class IITBombayIngestionTests(unittest.TestCase):
    def read_csv(self, contents: str) -> pd.DataFrame:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "apartment.csv"
            path.write_text(contents, encoding="utf-8")
            return read_iit_bombay(path)

    def test_epoch_seconds_remain_the_same_utc_instant(self):
        observations = self.read_csv(
            "TS,W1,W2,W3\n1481729400,1,2,3\n"
        )

        self.assertEqual(
            observations.loc[0, "reading_time"],
            pd.Timestamp("2016-12-14T15:30:00Z"),
        )
        self.assertEqual(observations.loc[0, "consumption_value"], 6)
        self.assertEqual(observations.loc[0, "source_row_number"], 2)

    def test_incomplete_phase_total_fails_canonical_validation(self):
        observations = self.read_csv(
            "TS,W1,W2,W3\n1481729400,1,,3\n"
        )

        self.assertTrue(pd.isna(observations.loc[0, "consumption_value"]))
        with self.assertRaisesRegex(ValueError, "malformed timestamp or target"):
            validate_observations(observations)


if __name__ == "__main__":
    unittest.main()
