# AWS Services Planning

| AWS service | Planned responsibility |
|---|---|
| AWS IoT Greengrass | Run local preprocessing, training and protected-update preparation on campus edge nodes. |
| AWS IoT Core | Receive protected MQTT model updates over mutual TLS and notify clients about global checkpoints. |
| AWS Lambda | Validate event schemas, orchestrate metadata updates and run the load-optimisation workflow. |
| Amazon S3 | Store model checkpoints, approved update artefacts, dataset manifests and dashboard exports. |
| Amazon DynamoDB | Store client registration, aggregation-round status, tariff schedules, optimisation results and alert state. |
| Amazon SageMaker | Run quality-weighted federated aggregation and managed model evaluation jobs. |
| Amazon API Gateway | Expose authenticated REST endpoints for dashboard data and building-control actions. |
| Amazon Cognito | Authenticate facility managers and issue dashboard user tokens. |
| AWS IAM | Enforce least-privilege permissions for users, edge devices and AWS services. |
| Amazon CloudWatch | Collect logs, metrics and alarms for ingestion, aggregation and optimisation health. |
| Amazon SNS | Send peak-demand, failed-update and threshold-breach notifications by email or SMS. |
| Amazon QuickSight | Create executive views of demand, savings, model quality and client participation. |
