# Workflow and Evaluation Plan

## End-to-end workflow

1. Campus sensors send energy and contextual telemetry to a Greengrass edge node.
2. The edge node validates, resamples and prepares local features, then trains its local forecasting model.
3. The node adds differential-privacy noise and a secure-aggregation mask to the model update.
4. IoT Core receives the update; Lambda validates its schema and records participation in DynamoDB.
5. SageMaker aggregates validated updates, weighting them by data quality, and stores the global checkpoint in S3.
6. IoT Core notifies edge clients to retrieve the latest checkpoint and continue local fine-tuning.
7. Lambda combines the forecast with tariff and flexible-load constraints to generate a 15-minute schedule.
8. API Gateway sends approved actions to the building-management system; the dashboard presents forecasts, alerts and estimated savings.

## Evaluation metrics

| Area | Metric | Success criterion |
|---|---|---|
| Forecasting | MAE, RMSE, MAPE and CV-RMSE | Compare federated model with local-only and centralised baselines |
| Demand control | Peak demand reduction | At least 20% against unscheduled baseline |
| Cost | Daily / monthly tariff cost saving | Positive saving after all flexible-load constraints |
| Privacy trade-off | Error versus privacy budget epsilon | Report effect of increasing privacy noise |
| Cold start | CV-RMSE and fine-tuning time | CV-RMSE below 25% where data permits |
| Reliability | Update success rate, aggregation latency and payload size | Monitor every federated round in CloudWatch |

## Acceptance checks

- No raw client telemetry is uploaded as part of a federated model update.
- Every API request requires a Cognito-authenticated user or device identity.
- Optimisation respects user-approved HVAC comfort, EV-charging and battery constraints.
- Dashboard values clearly identify whether data is live, forecasted or simulated.
