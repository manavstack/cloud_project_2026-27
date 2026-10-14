# Raw Dataset Manifest

Raw sources are retained under `cloud datasets AWS uni/` to preserve the supplied filenames and provenance. They are not copied into this folder.

| Source | Forecast target | Cadence | Identity |
| --- | --- | --- | --- |
| IIT Bombay | Electricity, `W1 + W2 + W3` (Wh) | Hourly in the source workflow | Anonymous apartment |
| IIIT-Delhi | Building power (W) | One-minute input, hourly mean for FedAvg profile | Building/mains/UPS meter |
| La Trobe | Consumption, unit and timezone pending validation | 15 minutes in the source workflow | Campus and meter |
| University of Twente | Source columns labeled kWh | Sparse supplied extracts | Building CSV |
| Valahia UVTgv | Electricity and heat demand (kWh) | Hourly | ABR, C, ICSTM building |

The source parsers preserve the original filename and row number in PostgreSQL. No interpolation, unit conversion, or outlier removal occurs silently.

The FedAvg demo treats each eligible input file as a local client, normalizes its target using training rows only, and emits only the global normalized-profile weights and aggregate client metadata. Twente's supplied extracts are too short for a chronological holdout; La Trobe remains excluded pending source-contract validation. Raw data are not copied into this directory or committed.
