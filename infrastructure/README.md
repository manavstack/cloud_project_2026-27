# Deployment Guide — Federated Campus Energy Cloud

Complete instructions for deploying all AWS services and connecting them to the dashboard.

---

## Prerequisites

| Tool | Install |
|---|---|
| AWS CLI v2 | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| AWS SAM CLI | `pip install aws-sam-cli` |
| Python 3.12 | https://www.python.org/downloads/ |
| boto3 | `pip install boto3` |

Configure AWS credentials:
```bash
aws configure
# enter: Access Key, Secret Key, region (ap-south-1), output format (json)
```

---

## Step 1 — Deploy the SAM stack

```bash
# From the repo root
bash infrastructure/deploy.sh campus-energy-cloud ap-south-1
```

This will:
1. Create an S3 bucket for SAM artifacts
2. Build all 8 Lambda function packages
3. Deploy the CloudFormation stack (Cognito, API GW, Lambda, DynamoDB, S3, SNS)
4. Print the 5 output values you need for `aws-config.js`
5. Optionally seed DynamoDB with initial data

Expected output:
```
──────────────────────────────────────────────────────
OutputKey              OutputValue
──────────────────────────────────────────────────────
UserPoolId             ap-south-1_AbCdEfGhI
UserPoolClientId       1a2b3c4d5e6f7g8h9i0j
RestApiUrl             https://abc123.execute-api.ap-south-1.amazonaws.com/prod
WebSocketApiUrl        wss://xyz789.execute-api.ap-south-1.amazonaws.com/prod
ExportBucketName       campus-energy-exports-123456789-ap-south-1
──────────────────────────────────────────────────────
```

---

## Step 2 — Fill in aws-config.js

Open `src/frontend/aws-config.js` and replace each `REPLACE_ME` with the values from step 1:

```js
window.AWS_CONFIG = {
  region: 'ap-south-1',
  cognito: {
    userPoolId:          'ap-south-1_AbCdEfGhI',   // ← UserPoolId
    userPoolWebClientId: '1a2b3c4d5e6f7g8h9i0j',   // ← UserPoolClientId
  },
  apiGateway: {
    restUrl: 'https://abc123.execute-api.ap-south-1.amazonaws.com/prod',
  },
  websocket: {
    url: 'wss://xyz789.execute-api.ap-south-1.amazonaws.com/prod',
  },
  s3: {
    exportBucket: 'campus-energy-exports-123456789-ap-south-1',
  },
};
```

---

## Step 3 — Create a Cognito user

```bash
# Create a test user
aws cognito-idp admin-create-user \
  --user-pool-id ap-south-1_AbCdEfGhI \
  --username your@email.com \
  --temporary-password Temp1234! \
  --user-attributes Name=email,Value=your@email.com Name=email_verified,Value=true

# Set a permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-south-1_AbCdEfGhI \
  --username your@email.com \
  --password YourPass123! \
  --permanent
```

---

## Step 4 — Run the dashboard

```bash
python3 -m http.server 8000
# open http://localhost:8000/src/frontend/
```

The dashboard will show the **Cognito login modal**. Sign in with the credentials from Step 3.

After login you will see:
- **"Live telemetry"** green badge (instead of Demo Mode)
- All KPI values pulled from DynamoDB via API Gateway
- Federation table refreshing from WebSocket in real time
- CSV export downloading via S3 pre-signed URL

---

## Optional — SageMaker integration

Deploy a SageMaker real-time endpoint with your trained CNN-LSTM model, then update the stack:

```bash
sam deploy \
  --template-file infrastructure/template.yaml \
  --stack-name campus-energy-cloud \
  --parameter-overrides SageMakerEndpointName=campus-energy-forecast-endpoint \
  --no-confirm-changeset
```

---

## Optional — IoT Core integration

1. Find your IoT Core ATS endpoint:
   ```bash
   aws iot describe-endpoint --endpoint-type iot:Data-ATS
   ```
2. Re-deploy with the endpoint:
   ```bash
   sam deploy ... --parameter-overrides IoTEndpoint=abcdef-ats.iot.ap-south-1.amazonaws.com
   ```

---

## Tear down

```bash
aws cloudformation delete-stack --stack-name campus-energy-cloud
```

> **Note:** The S3 export bucket must be emptied manually before the stack can be fully deleted.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Dashboard still shows Demo Mode after filling config | Hard-reload: Cmd+Shift+R |
| CORS error on API call | Check Cognito token expiry (8h); re-login |
| 403 on API Gateway | Ensure user is in Cognito user pool and token is valid |
| WebSocket not connecting | Check `websocket.url` in aws-config.js starts with `wss://` |
| CSV export 404 | Run a federation round or use seed script to create the S3 object |
