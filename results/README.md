# Results

`federated_demo/weights.json` is the reproducible output of `python -m src.federated.train`. It records the five global FedAvg weight vectors (one per round), participating client inventory, normalized chronological holdout metrics, and explicit exclusions. The artifact contains neither source rows nor individual client update vectors.

The FedAvg metric is dimensionless because each client normalizes targets with a training-only local scale. Do not interpret it as an absolute Wh/W/kWh forecast or compare it directly with the centralized dashboard's physical-unit MAE/RMSE. The profile model is not a production forecast.

For every centralized forecasting result, include MAE, RMSE, target unit, forecast horizon, cadence, asset count, test period, excluded-data rate, and Git commit. Compare it with persistence and seasonal-naive chronological baselines before making a performance claim.
