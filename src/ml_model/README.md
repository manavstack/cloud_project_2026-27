# Model Layer

The local dashboard loads canonical observations from PostgreSQL, shows source/asset coverage and daily energy totals, and trains a pooled `HistGradientBoostingRegressor` for the selected dataset contract (source, energy vector, unit, and interval). Contracts are selected and trained separately so values with different physical meanings or scales are never mixed. Evaluation uses an 80/20 chronological holdout and compares MAE/RMSE with a 24-observation seasonal-persistence baseline. Training metadata, data checksum, split, and feature definitions are written to `experiment_runs`; the local model artifact is written under ignored `models/`.

Forecasts are recursive and limited to 168 intervals. They use the selected asset's prior observed rows for lag features and return values in that source's unit. Because source gaps are retained without interpolation, observation lags do not always represent exact elapsed time; the dashboard reports cadence gaps. IIT data ends in June 2018; the reconstructed Valahia records end on December 30, 2020 because the supplied 2020 files contain 8,760 rows rather than the 8,784 hours of leap year 2020. All forecasts are historical projections, not current live predictions. Do not combine energy vectors, units, or sampling intervals.

This is a single-contract model, not yet the Hybrid Adaptive Mixture-of-Experts experiment. `HybridAdaptiveMoE` remains available for later experiments; meaningful multi-expert evaluation requires validating units/timezones and aligning additional sources first. La Trobe remains ineligible while its source unit is unconfirmed.

Run `python -m src.backend.app`, open `http://127.0.0.1:8000`, and use **Train & evaluate** to fit the model against the locally stored dataset.
