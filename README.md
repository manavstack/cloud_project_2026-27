# FEDRA Cloud Energy Prediction

Feature 1 is a reproducible energy-forecasting foundation for smart-university data. It validates heterogeneous sources before storing them in PostgreSQL and evaluates source-specific forecasts against chronological baselines.

## Student 1 scope

Manav Mishra (24BIT0100) owns the Feature 1 data, database, reproducibility, and model-integration foundation on the `feature1` branch.

## Architecture

Raw IIT Bombay, IIIT-Delhi, La Trobe, Valahia, and University of Twente files are retained under the supplied dataset directory. The PostgreSQL dashboard trains separate models for each compatible source/vector/unit/cadence contract. A separate, reproducible FedAvg demonstration trains campus/building clients locally on normalized time-of-week profiles, then aggregates compatible model parameters without combining raw records or physical units. It is a single-machine simulation, not a deployed multi-campus federation or the Hybrid Adaptive Mixture-of-Experts model.

See [AWS architecture](architecture/AWS_Architecture.svg), [system architecture](architecture/System_Architecture.svg), and [workflow](architecture/Workflow.svg).

## Quick start

1. Copy `.env.example` to `.env` and enter local PostgreSQL credentials for `cloud_project` on port `5432`.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Run the data-local federated experiment: `python -m src.federated.train`. It writes global round weights and approved client metadata to `results/federated_demo/weights.json`.
4. Create the PostgreSQL schema: `python -c "from src.db import apply_migrations; apply_migrations()"`.
5. Load a reviewed source with `python -m src.ingest.load iit "cloud datasets AWS uni/IIT-B - H"`.
6. (Optional) Load Valahia data with `python -m src.ingest.load valahia "<path-to-Valahia-data-directory>"`.
7. Start the local analytics and forecasting dashboard: `python -m src.backend.app`, then open `http://127.0.0.1:8000`. Choose a dataset contract in the selector, then use **Train & evaluate**. The federated section displays saved FedAvg weights and per-client normalized holdout metrics.

Do not commit `.env`, raw credentials, processed data, or serialized models.

The dashboard reports the selected contract's observations, asset coverage, daily totals, and per-asset statistics. Its centralized forecasting experiment evaluates a pooled gradient-boosting model against a 24-step seasonal baseline using an 80/20 chronological holdout, logs metadata in PostgreSQL, and saves the trained artifact under ignored `models/`. The independent FedAvg profile learner has its own chronological split and local normalization scale; it does not produce an absolute-energy forecast from the global weights alone. La Trobe is excluded until its source unit and timezone are confirmed; Twente files do not meet the minimum local holdout size. These are historical datasets; forecasts are not live readings. See [Dataset Details](docs/Dataset_Details.md) and the [federated workflow](src/federated/README.md) for provenance, limitations, and interpretation.

The current recorded FedAvg run used 59 eligible clients: 38 IIT Bombay apartments, 9 IIIT-Delhi buildings, and 12 Valahia building/year/vector files. Its round-by-round global weights and explicit exclusions are in [the federated result artifact](results/federated_demo/weights.json) and a [presentation-ready result summary](presentation/Federated_Training_Results.md). The interactive view is served from `/api/federated`.

## Repository map

- `architecture/` — project and AWS diagrams.
- `dataset/` — raw-data manifest and generated-data policy.
- `database/` — PostgreSQL migrations.
- `docs/` — workflow, dataset, and report material.
- `src/` — ingestion, backend, ML, AWS, and federated boundaries.
- `results/` — generated evaluation evidence.
- `presentation/` — review-deck outline.
- `architecture/Federated_Workflow.svg` — local training, weighted aggregation, and global-weight return loop.
