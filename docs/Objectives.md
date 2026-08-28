# Project Objectives

1. Develop an edge-based CNN-LSTM/GRU forecasting workflow that predicts each building's short-term electrical demand without uploading raw sensor data.
2. Build an event-driven AWS pipeline using IoT Core, Greengrass, Lambda, S3, DynamoDB and SageMaker to exchange protected model updates and publish global model checkpoints.
3. Protect federated training with local Gaussian differential privacy and pairwise secure aggregation, and compare forecast quality under different privacy budgets.
4. Implement a tariff-aware optimisation service that schedules HVAC, EV charging and battery loads in 15-minute intervals, targeting at least 20% peak-demand reduction.
5. Support cold-start campus buildings through transfer fine-tuning, with a target CV-RMSE below 25% after onboarding.
6. Provide authenticated operational dashboards and alerts for facility managers, including demand forecasts, model-round health, error variance and estimated cost savings.
