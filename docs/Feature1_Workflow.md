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

## Planned module ownership

- `src/ingest/`: source-specific parsers and validation.
- `src/ml_model/`: chronological baselines, source experts, gradient-based gating, and EW reliability updates.
- `src/backend/`: database-backed application endpoints.
- `src/federated/`: deferred until the centralized workflow is reproducible.
