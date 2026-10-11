# FEDRA Cloud Energy Prediction

Feature 1 is a reproducible energy-forecasting foundation for smart-university data. It ingests three heterogeneous sources into PostgreSQL, protects their source and asset identity, and evaluates chronological baselines before using the Hybrid Adaptive Mixture-of-Experts model.

## Student 1 scope

Manav Mishra (24BIT0100) owns the Feature 1 data, database, reproducibility, and model-integration foundation on the `feature1` branch.

## Architecture

Raw IIT Bombay, La Trobe, and Valahia files are parsed source-by-source, validated against one canonical observation contract, and stored in PostgreSQL. Source experts produce aligned forecasts. A gradient-trained gate combines them with exponentially weighted reliability that is updated only after the observed target is available.

See [AWS architecture](architecture/AWS_Architecture.svg), [system architecture](architecture/System_Architecture.svg), and [workflow](architecture/Workflow.svg).

## Quick start

1. Copy `.env.example` to `.env` and enter local PostgreSQL credentials for `cloud_project` on port `5432`.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Create the schema: `python -c "from src.db import apply_migrations; apply_migrations()"`.
4. Load a reviewed source with `python -m src.ingest.load iit "cloud datasets AWS uni/IIT-B - H"`.

Do not commit `.env`, raw credentials, processed data, or serialized models.

## Repository map

- `architecture/` — project and AWS diagrams.
- `dataset/` — raw-data manifest and generated-data policy.
- `database/` — PostgreSQL migrations.
- `docs/` — workflow, dataset, and report material.
- `src/` — ingestion, backend, ML, AWS, and federated boundaries.
- `results/` — generated evaluation evidence.
- `presentation/` — review-deck outline.
