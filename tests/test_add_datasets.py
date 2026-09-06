import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_registry_keys():
    # import the registry from add_datasets
    import add_datasets as ad

    registry = ad._spec_registry()
    assert "nasa_power" in registry
    assert "bdg2" in registry


def test_nasa_processed_exists():
    # If the user ran the nasa_power step earlier, the processed file should exist.
    p = ROOT / "data" / "processed" / "nasa_power.parquet"
    # test is lenient: file may not exist in CI, so mark xfail if missing
    if not p.exists():
        pytest.xfail("nasa_power.parquet not present; run add_datasets.py --dataset nasa_power first")
    assert p.exists()
