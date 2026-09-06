Data directory
==============

Structure used by dataset ingestion tooling:

- `data/raw/` : raw downloaded archives and API responses (git clones, JSON, CSVs)
- `data/processed/` : normalized parquet files following the project's common schema

Guidelines:
- Add raw files under `data/raw/<dataset_key>/` (the scripts are idempotent and will skip existing files).
- Processed parquet files are written to `data/processed/<dataset_key>.parquet`.

Example:
```
data/raw/nasa_power/weather_raw.json
data/processed/nasa_power.parquet
```
