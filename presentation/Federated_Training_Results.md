# Campus Energy FedAvg — Presentation Results

## Problem and proposal

Smart-campus meters are distributed across buildings and institutions. Pooling all raw readings centrally creates data-governance and privacy barriers, while differing units, timezones, and sampling rates make direct multi-campus training unsafe. This prototype trains one local time-of-week profile per eligible dataset, keeps raw records and local scale out of the shared artifact, and aggregates model parameters with sample-count-weighted FedAvg.

## Executed experiment

- **Model:** five-parameter linear profile (`hour_sin`, `hour_cos`, `weekday_sin`, `weekday_cos`, `bias`).
- **Target:** client-local mean-absolute-normalized demand. This is dimensionless; the global vector alone cannot output Wh, W, or kWh.
- **Validation:** each client is sorted by time and split 80% train / 20% later holdout. Features use the documented campus-local timezone.
- **Training:** five FedAvg rounds; 20 local full-batch gradient steps per round; clients are weighted by their number of training rows.
- **Participants:** 59 total — 38 IIT Bombay apartment datasets, 9 IIIT-Delhi building datasets, and 12 Valahia building/year/vector datasets.
- **Rows:** 478,298 training profile rows and 119,591 held-out profile rows across participants. IIIT-Delhi one-minute watts are first aggregated into local-hour mean watts.
- **Artifacts:** complete round-by-round global weights, normalized local metrics, participant inventory, and exclusions are saved in [`results/federated_demo/weights.json`](../results/federated_demo/weights.json).

## Final global weights

| Parameter | Value |
| --- | ---: |
| `hour_sin` | -0.037406 |
| `hour_cos` | -0.088405 |
| `weekday_sin` | 0.055572 |
| `weekday_cos` | -0.016105 |
| `bias` | 0.998070 |

The artifact contains all five values after each aggregation round. The FEDRA dashboard reads the saved artifact and displays the final vector, round history, participating clients, and exclusions.

## Local holdout summary

Values are the **median across clients** in each source. Errors are dimensionless normalized MAE and are not directly comparable across source populations or with physical-unit forecasts.

| Source | Clients | Median model MAE | Median local-mean baseline MAE | Clients beating baseline |
| --- | ---: | ---: | ---: | ---: |
| IIIT-Delhi | 9 | 0.368 | 0.377 | 8 / 9 |
| IIT Bombay | 38 | 0.886 | 0.897 | 27 / 38 |
| Valahia UVTgv | 12 | 1.037 | 1.037 | 6 / 12 |

The profile model only modestly improves these simple baselines and the Valahia median is slightly worse. This is a feasibility demonstration, not evidence of statistically significant improvement or operational readiness.

## Excluded datasets

- **IIT Bombay apartment 13:** 37 valid rows, below the 500-row minimum for a local train/holdout.
- **University of Twente:** nine extracts contain only 32–33 rows each, below the same minimum.
- **La Trobe:** excluded until its unit and timezone are documented and validated.
- **IIIT-Delhi aggregate and transformer files:** not treated as additional building clients because their totals overlap the selected building meters.

The exclusions are machine-readable in the result artifact. The workflow does not manufacture missing readings, infer an unverified unit, or silently fold duplicate totals into training.

## Privacy and deployment boundary

The current execution is a **single-machine FedAvg simulation**: local client preparation and parameter aggregation run in one process. Raw observations and private normalization scales are not placed in the result artifact; per-client update vectors are not persisted. Model updates can nevertheless leak information, and this prototype has no campus network, authenticated clients, encrypted transport, secure aggregation, differential privacy, or malicious-client defenses. A real deployment requires data-owner approval, a reviewed privacy threat model, protected aggregation, and client-side scale restoration before converting predictions to each campus's physical units.

## Reproduce and demonstrate

1. Keep source datasets in `cloud datasets AWS uni/`.
2. From the repository root, run `python -m src.federated.train`.
3. Run the local app with `python -m src.backend.app` and open `http://127.0.0.1:8000`.
4. Present the **Campus-local training · FedAvg weights** section alongside the centralized dashboard, making clear that they are separate experiments.
