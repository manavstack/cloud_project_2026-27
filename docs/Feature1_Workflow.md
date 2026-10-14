# Feature 1 Workflow

Feature 1 implements the workflow in `cloud_project_workflow.docx` for Student 1 on the existing `feature1` branch. It establishes persistent canonical storage before data ingestion, baseline training, and the hybrid adaptive mixture-of-experts experiment.

## Scope

- Preserve source identity, site, asset, timestamps, units, cadence, source file, and row provenance.
- Keep electricity and heat in separate `energy_vector` values.
- Use chronological training, validation, and test windows; never random-shuffle time series by default.
- Store a prediction before its eventual observed value. Exponentially weighted reliability can be updated only after observation, for a subsequent prediction.
- Require target-unit, forecast-horizon, interval, and feature alignment before expert forecasts are combined.

## PostgreSQL

The local database target is `cloud_project` at `127.0.0.1:5432`. Configuration is environment-only; copy `.env.example` to `.env` locally and never commit real credentials. `python-dotenv` loads this local file when the application starts.

Install the client dependency and apply the migration:

```bash
pip install -r requirements.txt
python -c "from src.db import apply_migrations; apply_migrations()"
```

`database/migrations/001_feature1_canonical_schema.sql` creates canonical observations, reproducibility records, exponentially weighted reliability history, and MoE prediction audit records.

Load one source at a time after reviewing its unit and timestamp assumptions:

```bash
python -m src.ingest.load iit "cloud datasets AWS uni/IIT-B - H"
python -m src.ingest.load valahia "cloud datasets AWS uni/valahia uni of targoviste - O/UVTgv_OD/demand"
python -m src.ingest.load la-trobe "cloud datasets AWS uni/la trobe uni - H/building_consumption.csv.zip"
```

La Trobe loading streams its archive in chunks. Its source unit remains `pending_validation`, so it is not eligible for mixed-unit MoE output until documented conversion/alignment is supplied.

## Campus-local FedAvg demonstration

Run `python -m src.federated.train` to train the eligible local datasets and save `results/federated_demo/weights.json`. The current run treats IIT Bombay apartment files, IIIT-Delhi building files, and Valahia building/year/vector files as separate clients. Each client uses its documented campus timezone, derives cyclic hour/weekday features, normalizes target values by a training-only local scale, and uses an 80/20 chronological split. FedAvg averages each client's parameter vector by its local training-row count for five rounds.

The shared linear profile has five parameters: `hour_sin`, `hour_cos`, `weekday_sin`, `weekday_cos`, and `bias`. The report contains the final global vector and one global vector per round; it does not persist per-client update vectors or raw observations. The dashboard's federated panel reads this report from `/api/federated`.

This is a single-machine algorithm demonstration. It has no network clients, transport encryption, secure aggregation, differential privacy, or adversarial-client protection. La Trobe is excluded while its unit/timezone are unverified. Twente is excluded because its current extracts are too short for the minimum training and chronological holdout. The aggregate model predicts normalized relative profiles only; absolute demand scaling stays local and must be restored on the campus before any operational use.

## Module ownership

- `src/ingest/`: source-specific parsers and validation.
- `src/ml_model/`: centralized chronological baselines, model service, and forecasting.
- `src/backend/`: dashboard API and local static-file server.
- `src/federated/train.py`: source-specific local preparation, individual client training, chronological local evaluation, and weighted FedAvg.
