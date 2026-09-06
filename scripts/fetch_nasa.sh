#!/usr/bin/env bash
# Helper to fetch NASA POWER for the default lat/lon
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 "$ROOT/add_datasets.py" --dataset nasa_power --out "$ROOT/data/processed"
