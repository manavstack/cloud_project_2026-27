import tempfile
import unittest
from pathlib import Path

from src.ingest.valahia import read_valahia
from src.validation import validate_observations


class ValahiaIngestionTests(unittest.TestCase):
    def test_accepts_documented_single_column_with_source_specific_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "UVTgv_elec_demand_building_C_2019.csv"
            path.write_text("Cx3\n1.5\n2.5\n", encoding="utf-8")

            observations = validate_observations(read_valahia(path))

        self.assertEqual(observations["unit"].unique().tolist(), ["kWh"])
        self.assertEqual(observations["energy_vector"].unique().tolist(), ["electricity"])
        self.assertEqual(observations["consumption_value"].tolist(), [1.5, 2.5])

    def test_rejects_multiple_demand_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "UVTgv_elec_demand_building_C_2019.csv"
            path.write_text("first,second\n1,2\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exactly one demand column"):
                read_valahia(path)


if __name__ == "__main__":
    unittest.main()
