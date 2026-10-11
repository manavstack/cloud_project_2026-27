# Deployment Guide: Smart Campus Energy Cloud

Complete instructions for deploying all AWS services and connecting them to the dashboard.
Based on the project design in `Cloud_Project.pdf` (IoT ingestion, forecasting, tariff-aware control, alerts, secure dashboard).

## Files

| File | Purpose |
|---|---|
| `template.yaml` | AWS SAM template: IoT rule, Lambdas, S3, DynamoDB, SNS, Cognito, HTTP API, SageMaker role, CloudWatch |
| `deploy.sh` | One-command build, deploy, seed, outputs, destroy |
| `edge_provision.py` | Seed data, register building gateways (IoT certificates), simulate telemetry, cleanup |
| `src/preprocess/` | IoT message -> validate -> S3 + DynamoDB + peak/anomaly alerts |
| `src/forecast/` | 15 and 30 minute demand forecast (baseline, or your SageMaker endpoint) |
| `src/control_policy/` | Tariff and comfort rules, recommended actions, SNS notification |
| `src/api/` | Dashboard API behind Cognito |

## Prerequisites

| Tool | Install |
|---|---|
| AWS account + credentials | `aws configure` or `aws sso login` |
| AWS CLI v2 | https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html |
| AWS SAM CLI | https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html |
| Python 3.12 + boto3 | `pip install boto3` |

## Architecture

```
Smart meters / sensors -> AWS IoT Core (campus/<building>/telemetry)
        -> Lambda preprocess -> S3 (raw) + DynamoDB (structured) + SNS (peak/anomaly alerts)
        -> Lambda forecast (every 15 min; baseline or SageMaker endpoint) -> DynamoDB forecasts
        -> Lambda control policy (every 15 min) -> recommended actions + SNS
API Gateway (HTTP API) + Cognito JWT -> Lambda api -> dashboard
CloudWatch: logs, error alarms, ops dashboard
```

Note: structured storage uses DynamoDB instead of the RDS/Aurora in the report. It keeps the stack fully serverless, near-zero cost when idle, and needs no VPC. State this in your slides if you present the deployed version.

## 1. Deploy

```bash
cd infrastructure
export ALERT_EMAIL="you@example.com"      # optional
export AWS_REGION="ap-south-1"            # optional, default ap-south-1
./deploy.sh
```

`deploy.sh` validates the template, builds, deploys the stack (`smart-campus-energy-dev` by default), seeds the buildings and tariff windows, and prints the outputs. Confirm the SNS email subscription when it arrives.

Optional settings: `PEAK_THRESHOLD_KW` (default 50), `TIMEZONE` (default Asia/Kolkata), `CORS_ORIGIN`, `SAGEMAKER_ENDPOINT`, `STACK_NAME`.

## 2. Register building gateways

```bash
python3 edge_provision.py --stack smart-campus-energy-dev provision --building lab_1
```

Creates an IoT thing and certificate, attaches the device policy, and saves credentials to `certs/<thing>/` (git-ignored). Gateways connect with client id = thing name and publish JSON to `campus/<building_id>/telemetry`:

```json
{"ts": "2026-10-11T10:15:00Z", "power_kw": 12.4, "voltage_v": 231.0,
 "temperature_c": 26.1, "humidity_pct": 55, "occupancy_count": 34}
```

Use the AWS IoT Device SDK on the gateway (or a Zigbee2MQTT bridge as in the surveyed gateway paper). Devices can only connect as themselves and publish to `campus/*/telemetry`.

## 3. Test the pipeline without hardware

```bash
python3 edge_provision.py --stack smart-campus-energy-dev simulate --building lab_1 --count 20
python3 edge_provision.py --stack smart-campus-energy-dev seed --peak-now      # makes the current hour a peak window (demo)
aws lambda invoke --function-name smart-campus-energy-dev-forecast /dev/stdout
aws lambda invoke --function-name smart-campus-energy-dev-control /dev/stdout
```

Check: objects under `readings/` in the raw bucket, rows in the DynamoDB `readings` table, `control_actions` rows, and an alert email. To raise a peak alert, run simulate with `--base-kw 90`. Remove the `demo-peak-now` item from the tariff table afterwards.

## 4. Dashboard users

```bash
POOL=$(aws cloudformation describe-stacks --stack-name smart-campus-energy-dev \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text)
CLIENT=$(aws cloudformation describe-stacks --stack-name smart-campus-energy-dev \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" --output text)

aws cognito-idp admin-create-user --user-pool-id $POOL --username you@example.com
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL --username you@example.com --group-name admin
# (use group facility_staff for read-only facility managers)

aws cognito-idp initiate-auth --client-id $CLIENT --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=you@example.com,PASSWORD='<your password>'
```

The first sign-in requires changing the temporary password. Use the returned `IdToken` as the bearer token. `USER_PASSWORD_AUTH` is enabled for CLI testing; remove it from `template.yaml` for production and use SRP or the hosted UI (`CognitoDomain` output).

## 5. Dashboard API

```bash
API=$(aws cloudformation describe-stacks --stack-name smart-campus-energy-dev \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
curl -H "Authorization: Bearer <IdToken>" "$API/readings?building_id=lab_1&limit=10"
```

| Route | Parameters |
|---|---|
| `GET /buildings` | none |
| `GET /readings` | `building_id` (required), `from`, `to`, `limit` |
| `GET /forecasts` | `building_id` (required), `from`, `to`, `limit` |
| `GET /actions` | `building_id`, `from`, `to`, `limit` |
| `GET /alerts` | `building_id`, `from`, `to`, `limit` |

`from` and `to` are ISO-8601; `limit` defaults to 100 (max 500). Callers must be in the Cognito group `admin` or `facility_staff`. Set `CORS_ORIGIN` to your dashboard URL when you deploy a frontend.

## 6. Forecasting with SageMaker

The stack ships with a persistence baseline so the control loop works from day one. To use a trained model:

1. Export history from the raw bucket (`readings/` partitions) or DynamoDB; train in SageMaker with the `SageMakerRoleArn` output. Use a chronological split (for example 70/20/10) and target MAPE under 10%.
2. Deploy a real-time endpoint that accepts `{"building_id", "recent_kw": [...], "horizon_min", "ts"}` and returns `{"predicted_kw": <number>}`.
3. Redeploy with `SAGEMAKER_ENDPOINT=<endpoint-name> ./deploy.sh`. If the endpoint fails, the forecaster falls back to the baseline and logs the error.

## 7. Dashboards (QuickSight)

QuickSight needs an account subscription and is not part of the stack. Either build the dashboard on the API above, or export tables to S3 and query them with Athena, then connect QuickSight to Athena.

## 8. Monitoring

CloudWatch log groups have 30-day retention; each Lambda has an error alarm that notifies the SNS topic; an ops dashboard named `<stack>-ops` shows invocations and errors.

## 9. Cleanup

```bash
python3 edge_provision.py --stack smart-campus-energy-dev cleanup   # IoT things + certificates
./deploy.sh destroy                                                 # empties the raw bucket, deletes the stack
```

## Security summary

- S3: encrypted, versioned, public access blocked, TLS-only
- DynamoDB: encrypted at rest, point-in-time recovery on readings
- IAM: per-function least privilege through SAM policy templates
- Devices: certificate auth, publish only to `campus/*/telemetry`
- API: Cognito JWT plus group check inside the function, throttled, access-logged
- Not covered: WAF, KMS customer keys, multi-account setup, formal threat model

## Limitations

- Control actions are recommendations; nothing is sent to a building-management system yet
- Baseline forecast is a simple persistence model, not the target model
- The control engine re-notifies every 15 minutes while a peak is forecast
- Tariff windows must start and end within one day (no overnight windows)
- Checked with `cfn-lint` and unit tests against mocked AWS services, but not deployed to a real account; run `sam validate --lint` and a test deploy first
