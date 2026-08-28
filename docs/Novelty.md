# Novelty Summary

The project is distinct because it turns privacy-preserving federated forecasting into a complete operational loop rather than treating forecasting, security and scheduling as separate experiments.

## What is new

- **Closed-loop control:** protected federated forecasts directly drive tariff-aware HVAC, EV-charging and battery schedules.
- **Dual privacy layer:** Gaussian differential privacy limits exposure from local updates, while pairwise secure aggregation prevents the cloud aggregator from reading an individual update.
- **Adaptive federation:** aggregation weights account for client data quality and can be extended with client clustering when campus behaviour changes.
- **Cold-start operation:** a newly added facility can begin from the global model and locally fine-tune instead of waiting to collect a large local history.
- **Serverless AWS architecture:** IoT Core, Lambda, S3, DynamoDB, SageMaker, Cognito, API Gateway, CloudWatch and SNS are mapped to clear operational responsibilities.
- **Manager-facing visibility:** the dashboard translates technical model information into demand peaks, recommended actions, privacy status and cost savings.

Together, these features aim to make federated energy management more secure, scalable and useful for real facility operations.
