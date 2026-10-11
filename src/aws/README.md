# AWS Service Plan

| Service | Planned purpose |
| --- | --- |
| Amazon S3 | versioned raw-data manifests and approved model artifacts |
| Amazon RDS for PostgreSQL | managed equivalent of the local canonical store |
| AWS Lambda | scheduled validation and inference jobs |
| Amazon API Gateway | authenticated forecast and health APIs |
| AWS IAM and Secrets Manager | least-privilege access and secret storage |
| Amazon CloudWatch | logs, metrics, and ingestion alarms |

This is a deployment plan only. The local ingestion-to-evaluation workflow is the prerequisite for provisioning cloud resources.
