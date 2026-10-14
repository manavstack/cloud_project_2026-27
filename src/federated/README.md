# Campus-local FedAvg demonstration

Run from the repository root after the supplied raw datasets are available:

```bash
python -m src.federated.train
```

The command trains each eligible dataset locally, applies an 80/20 chronological split per client, and writes a reproducible report to `results/federated_demo/weights.json`. Change the input directory or output path with `--data-root` and `--output`; change the aggregation rounds with `--rounds`.

## Model and transfer

Each client computes four cyclic features from its documented local clock (hour-of-day and day-of-week sine/cosine) and locally normalizes consumption by the training window's mean absolute target. A five-parameter linear model predicts that dimensionless relative profile. Each round starts from the latest global vector, trains one local model per eligible dataset, then computes the sample-count-weighted FedAvg vector. The report shows the global weights for every round and the final global weights; raw records and individual client update vectors are not written to the report. Client-local normalization scales are not shared.

The current source adapters discover 39 IIT Bombay apartment files, nine IIIT-Delhi building files, and twelve Valahia building/year/vector files. The recorded run trained 38, nine, and twelve clients respectively; IIT Bombay apartment 13 had only 37 valid rows and did not meet the 500-row minimum. The supplied Twente extracts are also below that threshold. La Trobe is excluded because its unit and timezone have not been verified. IIIT-Delhi campus/transformer totals are excluded from the building-client set to avoid overlapping meters.

## Interpretation and limitations

FedAvg can share a relative daily/weekly profile across sources after normalization, but the global weights are not directly an absolute forecast in Wh, W, or kWh. A participating campus must retain its local scale and convert model outputs to the correct physical contract. The current command runs every client on one machine; it demonstrates local data preparation and parameter aggregation, not federation between campuses.

Model updates can still reveal information. Do not publish or transmit per-client updates without a data-owner review. A production deployment needs authenticated campus clients, encrypted transport, secure aggregation, explicit update/metric disclosure policies, privacy-risk assessment (and differential privacy if required), client-failure handling, and a versioned protocol. The demo provides none of these security/privacy guarantees.
