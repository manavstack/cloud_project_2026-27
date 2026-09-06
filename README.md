# Federated Campus Energy Cloud
### Cloud Computing Project — 2026-27 | VIT | Feature 2 (AWS Cloud Infrastructure & IoT Integration)

> A privacy-preserving, federated-learning-powered energy demand forecasting and flexible-load scheduling system for smart university campuses — deployed entirely on AWS serverless infrastructure.

---

## 🌐 Live URLs

| Resource | URL |
|----------|-----|
| **Frontend Dashboard** | http://campus-energy-frontend-585384908183.s3-website.ap-south-1.amazonaws.com |
| **REST API Base URL** | https://nzkopoif4a.execute-api.ap-south-1.amazonaws.com/prod |
| **WebSocket API** | wss://8gdus6lq60.execute-api.ap-south-1.amazonaws.com/prod |

### REST API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prod/forecast` | Latest predicted demand, hourly bars, peak reduction, savings |
| `GET` | `/prod/tariffs` | Current Time-of-Use tariff plan (INR/kWh, peak windows) |
| `GET` | `/prod/federation` | Latest federated learning round — client participation, privacy epsilon |
| `GET` | `/prod/schedule` | Active approved HVAC/EV/battery load schedule |
| `POST` | `/prod/schedule` | Approve a new schedule (writes to DynamoDB + publishes to IoT Core MQTT) |
| `GET` | `/prod/export` | Returns a 10-minute pre-signed S3 URL to download federation CSV |
| `POST` | `/prod/alerts` | SNS webhook — receives CloudWatch alarms, stores to DynamoDB, pushes to WebSocket |

---

## 🏗️ Architecture Overview

```
IoT Edge Device (campus building)
        │  MQTT (campus/bms/action, campus/edge/<id>/forecast)
        ▼
   AWS IoT Core
        │
   ┌────┴─────────────────────────────────────────────────────┐
   │                    AWS Cloud (ap-south-1)                 │
   │                                                           │
   │  Cognito User Pool ──► API Gateway (REST + WebSocket)    │
   │                               │                           │
   │         ┌─────────────────────┼──────────────────────┐   │
   │         ▼         ▼          ▼          ▼            ▼   │
   │    ForecastFn  TariffsFn  FedFn   ScheduleFn    AlertsFn │
   │         │         │          │          │            │    │
   │         └─────────┴──────────┴────►  DynamoDB       │    │
   │                                   (5 tables)        │    │
   │                                                     ▼    │
   │    ExportFn ──► S3 pre-signed URL         SNS Topic      │
   │                                                     │    │
   │    WsConnect/Disconnect ──► WsConnections table     │    │
   │    WebSocket API ◄──── AlertsFn broadcasts ◄────────┘    │
   │                                                           │
   │    SageMaker (optional) ◄─── ForecastFn fallback         │
   │    CloudWatch Logs ◄───── all Lambda functions            │
   └───────────────────────────────────────────────────────────┘
        │
   Frontend (S3 Static Website)
   index.html + app.js + styles.css + aws-config.js
```

---

## 📦 Project Structure

```
cloud_project_2026-27/
│
├── infrastructure/
│   ├── template.yaml          # SAM/CloudFormation — all AWS resources defined here
│   └── edge_provision.py      # IoT Core edge device provisioning script
│
├── src/
│   ├── backend/
│   │   ├── lambda/
│   │   │   ├── forecast/      # GET /forecast
│   │   │   │   └── handler.py
│   │   │   ├── federation/    # GET /federation
│   │   │   │   └── handler.py
│   │   │   ├── schedule/      # GET + POST /schedule
│   │   │   │   └── handler.py
│   │   │   ├── tariffs/       # GET /tariffs
│   │   │   │   └── handler.py
│   │   │   ├── alerts/        # POST /alerts (SNS webhook)
│   │   │   │   └── handler.py
│   │   │   ├── export/        # GET /export (S3 pre-signed URL)
│   │   │   │   └── handler.py
│   │   │   └── websocket/     # WebSocket $connect / $disconnect
│   │   │       ├── connect.py
│   │   │       └── disconnect.py
│   │   └── seed/
│   │       └── seed_dynamodb.py   # Populates all 5 DynamoDB tables with initial data
│   │
│   ├── frontend/
│   │   ├── index.html         # Dashboard UI (login, charts, KPIs, schedule approval)
│   │   ├── app.js             # All frontend logic — Cognito auth, API calls, charts
│   │   ├── styles.css         # Dark-mode premium UI
│   │   └── aws-config.js      # Live AWS endpoint configuration (filled in post-deploy)
│   │
│   └── ml_models/             # Local ML model for edge inference
│       ├── predict.py
│       ├── model.pkl
│       └── feature_columns.json
│
├── local_server/              # FastAPI edge proxy server
│   ├── main.py                # POST /predict — runs local ML model + pushes to IoT Core
│   ├── aws_client.py          # Boto3 IoT Core MQTT publisher helper
│   └── requirements.txt
│
├── dataset/                   # Energy consumption dataset (preprocessing + raw)
├── architecture/              # Architecture diagrams
├── docs/                      # Phase I report sections
├── presentation/              # Phase I presentation outline
└── results/                   # Experiment results
```

---

## ☁️ AWS Services Used

| Service | Purpose | Resource Name |
|---------|---------|---------------|
| **AWS Lambda** | Serverless compute for all API handlers | `campus-energy-forecast`, `campus-energy-tariffs`, `campus-energy-federation`, `campus-energy-schedule`, `campus-energy-alerts`, `campus-energy-export`, `campus-energy-ws-connect`, `campus-energy-ws-disconnect` |
| **API Gateway (REST)** | HTTP REST API for dashboard | `campus-energy-rest-api` (ID: `nzkopoif4a`) |
| **API Gateway (WebSocket)** | Real-time push for alerts | `campus-energy-ws` (ID: `8gdus6lq60`) |
| **Amazon Cognito** | User authentication (JWT) | Pool ID: `ap-south-1_2bm4YeRJ5`, Client: `5sitauocubcvtqbhh0birfiafv` |
| **Amazon DynamoDB** | All application data | 5 tables (see below) |
| **Amazon S3** | CSV export storage + frontend hosting | `campus-energy-exports-585384908183-ap-south-1`, `campus-energy-frontend-585384908183` |
| **Amazon SNS** | Alert fan-out (CloudWatch → Lambda) | `campus-energy-alerts` (ARN: `arn:aws:sns:ap-south-1:585384908183:campus-energy-alerts`) |
| **AWS IoT Core** | Edge device MQTT broker | Thing: `campus-energy-cloud-CampusEdgeNode`, Topic: `campus/bms/action` |
| **Amazon SageMaker** | Optional live ML inference endpoint | Pluggable via `SAGEMAKER_ENDPOINT_NAME` env var |
| **Amazon CloudWatch** | Lambda logs, billing alarms | Log groups: `/aws/lambda/campus-energy-*` (14-day retention) |
| **AWS IAM** | Lambda execution role + policies | `campus-energy-lambda-role` |
| **AWS SAM / CloudFormation** | Infrastructure as Code | Stack: `campus-energy-cloud` |

---

## 🗄️ DynamoDB Tables

| Table Name | Primary Key | Description | Seeded With |
|------------|-------------|-------------|-------------|
| `CampusEnergy-Forecasts` | `forecastId` (S) | Predicted demand snapshots. `forecastId="latest"` is always the most recent. PITR enabled. | 1 item (predicted demand 842 kW, 12-hr hourly bars, epsilon 0.31) |
| `CampusEnergy-FedRounds` | `roundId` (S) | Federated learning rounds. `roundId="latest"` = most recent aggregation result, with per-client quality/privacy stats. | 1 item (5 clients, round 42) |
| `CampusEnergy-Schedules` | `scheduleId` (S) | Approved HVAC/EV/battery schedules. `scheduleId="active"` = currently executing schedule. | 1 item (3 actions: HVAC setback, EV charging defer, battery discharge) |
| `CampusEnergy-Tariffs` | `tariffId` (S) | Time-of-Use tariff plans. `tariffId="current"` = active plan. | 1 item (ToU Campus Plan 2026-27, INR 6.5 off-peak / 12.4 peak) |
| `CampusEnergy-Alerts` | `alertId` (S) | Alert history from SNS/CloudWatch. TTL enabled (auto-expire old alerts). | 1 item |
| `CampusEnergy-WsConnections` | `connectionId` (S) | Active WebSocket client connections. Managed by connect/disconnect Lambdas. | — (populated at runtime) |

---

## 🔧 Lambda Functions — Detailed

### 1. `campus-energy-forecast` — `GET /forecast`
**File:** `src/backend/lambda/forecast/handler.py`

Returns the latest energy demand forecast to the dashboard.

- Reads `CampusEnergy-Forecasts` table (key: `forecastId = "latest"`)
- **Optional SageMaker integration:** if `SAGEMAKER_ENDPOINT_NAME` env var is set, calls the SageMaker real-time endpoint first and merges live predictions over DynamoDB data
- Falls back to DynamoDB if SageMaker is not configured or fails
- Adds a `source` field (`"sagemaker"` or `"dynamodb"`) in the response

**Response fields:** `predictedDemandKw`, `peakReductionPct`, `savingsINR`, `activeClients`, `privacyEpsilonAvg`, `hourlyBars` (12-entry list for hours 12–23), `targetCeilingKw`, `updatedAt`, `source`

---

### 2. `campus-energy-federation` — `GET /federation`
**File:** `src/backend/lambda/federation/handler.py`

Returns federated learning round data showing per-campus participation and privacy metrics.

- Reads `CampusEnergy-FedRounds` table
- Supports `?round=<roundNumber>` query parameter; defaults to `"latest"`
- Response includes per-client objects with: `clientId`, `campus`, `updateQuality`, `epsilon`, `sampleCount`, `weight`, `latencyMs`, `validated`

---

### 3. `campus-energy-schedule` — `GET + POST /schedule`
**File:** `src/backend/lambda/schedule/handler.py`

The most complex Lambda — reads and approves load-shift schedules, with IoT integration.

**GET:** Returns the active schedule from `CampusEnergy-Schedules` (key: `scheduleId = "active"`)

**POST:**
1. Parses the approved schedule from the request body
2. Extracts the Cognito username from JWT claims (`requestContext.authorizer.claims`)
3. Writes the schedule to DynamoDB with `approvedBy`, `approvedAt`, `status: "approved"`
4. Publishes an MQTT message to AWS IoT Core topic `campus/bms/action` with event `schedule_approved` so the physical BMS can act on it
5. IoT publish is skipped gracefully if `IOT_ENDPOINT` env var is not set

---

### 4. `campus-energy-tariffs` — `GET /tariffs`
**File:** `src/backend/lambda/tariffs/handler.py`

Returns the current Time-of-Use electricity tariff plan.

- Reads `CampusEnergy-Tariffs` table (key: `tariffId = "current"`)
- Used by the dashboard to show live tariff windows and by the optimisation logic to compute savings
- Response: `planName`, `currency`, `currentRateKwh`, `peakRateKwh`, `offPeakRateKwh`, `peakWindowStart`, `peakWindowEnd`, `updatedAt`

---

### 5. `campus-energy-alerts` — `POST /alerts`
**File:** `src/backend/lambda/alerts/handler.py`

SNS webhook that receives CloudWatch alarms and broadcasts them in real-time.

**Flow:** `CloudWatch Alarm → SNS Topic → HTTPS subscription → API Gateway → this Lambda`

- Handles SNS `SubscriptionConfirmation` (auto-confirms the subscription URL)
- Handles SNS `Notification` — parses the alert, stores it in `CampusEnergy-Alerts` with UUID, severity, and timestamp
- **Real-time WebSocket broadcast:** scans `CampusEnergy-WsConnections` for active connections and pushes the alert payload to every connected dashboard client via API Gateway Management API
- Automatically cleans up stale WebSocket connections (`GoneException` → delete from table)

---

### 6. `campus-energy-export` — `GET /export`
**File:** `src/backend/lambda/export/handler.py`

Generates a secure, time-limited download link for the federation round CSV.

- Generates an S3 pre-signed `GET` URL (default expiry: 600 seconds / 10 minutes)
- Points to `exports/federation_latest.csv` in the `campus-energy-exports-585384908183-ap-south-1` bucket
- The CSV is written by the SageMaker aggregation job after each federated round
- Returns: `downloadUrl`, `expiresInSeconds`, `filename`

---

### 7. `campus-energy-ws-connect` + `campus-energy-ws-disconnect`
**Files:** `src/backend/lambda/websocket/connect.py`, `disconnect.py`

Manage the WebSocket connection registry.

**Connect (`$connect` route):**
- Stores `connectionId`, `connectedAt`, `principal` (Cognito username) in `CampusEnergy-WsConnections`

**Disconnect (`$disconnect` route):**
- Deletes the connection record from `CampusEnergy-WsConnections`

---

## 🔐 Authentication & Security

- **Cognito User Pool** `ap-south-1_2bm4YeRJ5` — email/password login, 8-hour JWT tokens
- **API Gateway** — all routes open (no IAM restriction); Cognito JWT validation handled in `app.js`
- **Schedule POST** — extracts the Cognito `cognito:username` claim from the JWT passed in the `Authorization` header to record who approved the schedule
- **S3 exports** — never exposed publicly; access only via pre-signed URLs generated by the export Lambda
- **IAM Role** `campus-energy-lambda-role` — least-privilege policy: DynamoDB CRUD on the 6 tables, S3 GetObject/PutObject on the export bucket, IoT Publish on `campus/*` topic, SageMaker InvokeEndpoint, API Gateway WebSocket management

---

## 🤖 IoT Edge Integration

### AWS IoT Thing
- **Thing name:** `campus-energy-cloud-CampusEdgeNode`
- **Policy:** `campus-energy-cloud-EdgePolicy` — allows Connect, Publish, Subscribe, Receive on all topics

### IoT Topics
| Topic | Direction | Description |
|-------|-----------|-------------|
| `campus/bms/action` | Cloud → Device | Schedule approved — BMS executes HVAC/EV/battery actions |
| `campus/edge/<building_id>/forecast` | Device → Cloud | Edge-computed forecast from local ML model |

### Edge Provisioning Script
**File:** `infrastructure/edge_provision.py`

Automates IoT Core device registration:
- Creates the IoT Thing
- Generates X.509 certificate + private key
- Attaches the policy to the certificate
- Attaches the certificate to the Thing
- Outputs the ATS endpoint and certificate files for the physical edge device

---

## 🖥️ Local Edge Server

**Directory:** `local_server/`

A **FastAPI** server that runs on the campus edge node (e.g. Raspberry Pi or lab laptop). It:

1. Loads the trained ML model (`src/ml_models/model.pkl`) on startup
2. Exposes `POST /predict` — accepts 97+ telemetry readings (building ID, power kW, occupancy, temperature, humidity, is_weekend) and returns `forecast_kw`
3. After local inference, publishes the forecast to IoT Core via `aws_client.py` (topic: `campus/edge/<building_id>/forecast`)

**Input schema:**
```json
{
  "readings": [
    {
      "building_id": "A-Block",
      "timestamp": "2026-09-06T18:00:00Z",
      "power_kw": 342.5,
      "occupancy": 0.74,
      "temperature_c": 28.3,
      "humidity_pct": 65.0,
      "is_weekend": 0
    }
  ]
}
```

Run locally:
```bash
pip install -r local_server/requirements.txt
cd local_server
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 🌱 DynamoDB Seeding

**File:** `src/backend/seed/seed_dynamodb.py`

Populates all 5 operational tables with realistic initial data so the dashboard has something to show before any real federation rounds have run.

```bash
python src/backend/seed/seed_dynamodb.py
```

Seeded data includes:
- Forecast: 842 kW predicted demand, 12-hour hourly load bars, 15% peak reduction, ₹1,240 savings, 5/5 active clients
- Federation: Round 42, 5 campus clients (Main, Engineering, Hostel, Admin, Library blocks), privacy epsilon 0.28–0.35
- Schedule: 3 actions (HVAC setback 22°C, EV charging defer to 23:00, battery discharge 18:00–20:00)
- Tariffs: ToU Campus Plan 2026-27 (INR 6.5 off-peak, 12.4 peak, 3.2 off-peak night; peak 18:00–19:00)
- Alerts: 1 sample peak-demand breach alert

---

## 🖼️ Frontend Dashboard

**Hosted at:** http://campus-energy-frontend-585384908183.s3-website.ap-south-1.amazonaws.com

**Files:** `src/frontend/`

| File | Purpose |
|------|---------|
| `index.html` | Full dashboard HTML — login modal, KPI cards, charts, schedule panel, federation view, alerts panel |
| `app.js` | All JS logic — Cognito auth via AWS Amplify, REST API polling, WebSocket connection, chart rendering |
| `styles.css` | Dark-mode premium UI using CSS variables, Inter font, glassmorphism cards |
| `aws-config.js` | Stores all live AWS endpoint values (filled in post-deploy, safe to commit — no secrets) |

**Login credentials:**
- Email: `admin@campus.edu`
- Password: `Admin@1234!`

**Demo Mode vs Live Mode:**
- If `aws-config.js` has placeholder values → runs in **Demo Mode** (simulated data, no AWS needed)
- If filled with real values → **Live Mode** (calls real Lambda APIs, connects real WebSocket)

---

## 🚀 Deploy From Scratch

### Prerequisites
- Python 3.13 installed
- AWS CLI: `pip install awscli`
- AWS SAM CLI: `pip install aws-sam-cli`

### Step 1 — Configure AWS
```powershell
$env:Path += ";C:\Users\avikv\AppData\Roaming\Python\Python313\Scripts"
aws configure
# Enter: Access Key ID, Secret Access Key, Region: ap-south-1, Output: json
```

### Step 2 — Build
```powershell
cd C:\Users\avikv\.vscode\cloud_project_2026-27
sam build -t infrastructure/template.yaml
```

### Step 3 — Create S3 Artifacts Bucket
```powershell
aws s3api create-bucket --bucket campus-energy-cloud-sam-artifacts-ap-south-1 --region ap-south-1 --create-bucket-configuration LocationConstraint=ap-south-1
```

### Step 4 — Deploy Stack
```powershell
sam deploy --stack-name campus-energy-cloud --s3-bucket campus-energy-cloud-sam-artifacts-ap-south-1 --region ap-south-1 --parameter-overrides StageName=prod --no-fail-on-empty-changeset --no-confirm-changeset --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
```

### Step 5 — Seed Database
```powershell
python src/backend/seed/seed_dynamodb.py
```

### Step 6 — Update Frontend Config
Copy the deploy output values into `src/frontend/aws-config.js`

### Step 7 — Host Frontend on S3
```powershell
aws s3api create-bucket --bucket campus-energy-frontend-585384908183 --region ap-south-1 --create-bucket-configuration LocationConstraint=ap-south-1
aws s3api delete-public-access-block --bucket campus-energy-frontend-585384908183
aws s3api put-bucket-policy --bucket campus-energy-frontend-585384908183 --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::campus-energy-frontend-585384908183/*"}]}'
aws s3 website s3://campus-energy-frontend-585384908183 --index-document index.html --error-document index.html
aws s3 sync src/frontend/ s3://campus-energy-frontend-585384908183/
```

### Step 8 — Create Login User
```powershell
aws cognito-idp admin-create-user --user-pool-id ap-south-1_2bm4YeRJ5 --username admin@campus.edu --temporary-password Admin@1234! --region ap-south-1
aws cognito-idp admin-set-user-password --user-pool-id ap-south-1_2bm4YeRJ5 --username admin@campus.edu --password Admin@1234! --permanent --region ap-south-1
```

---

## 🛑 Teardown (Complete — Zero Charges)

```powershell
$env:Path += ";C:\Users\avikv\AppData\Roaming\Python\Python313\Scripts"

# Empty all S3 buckets first
aws s3 rm s3://campus-energy-exports-585384908183-ap-south-1 --recursive
aws s3 rm s3://campus-energy-cloud-sam-artifacts-ap-south-1 --recursive
aws s3 rm s3://campus-energy-frontend-585384908183 --recursive

# Delete the CloudFormation stack (deletes all Lambda, DynamoDB, API GW, Cognito, SNS, IoT, IAM, CloudWatch)
aws cloudformation delete-stack --stack-name campus-energy-cloud --region ap-south-1
aws cloudformation wait stack-delete-complete --stack-name campus-energy-cloud --region ap-south-1

# Delete S3 buckets
aws s3api delete-bucket --bucket campus-energy-exports-585384908183-ap-south-1 --region ap-south-1
aws s3api delete-bucket --bucket campus-energy-cloud-sam-artifacts-ap-south-1 --region ap-south-1
aws s3api delete-bucket --bucket campus-energy-frontend-585384908183 --region ap-south-1
```

---

## 📋 Key Fixes Applied During Feature 2 Development

| Issue | Root Cause | Fix Applied |
|-------|-----------|-------------|
| `Circular dependency between resources` | SAM's `AWS::Serverless::Api` with `DefaultAuthorizer` auto-generates `*PermissionStage` Lambda permission resources that depend on the API deployment, which depends on the permissions → cycle | Removed `DefaultAuthorizer` from `RestApi`; removed all `Auth:` blocks from function events; SAM no longer generates cyclic permission resources |
| `WsDisconnectPermission` SourceArn invalid | Typo: `${AWS$ACCOUNT_ID}` instead of `${AWS::AccountId}` | Fixed to `${AWS::AccountId}` |
| `DependsOn` inside `Properties` block | YAML keys were nested incorrectly under `Properties` instead of top-level resource | Moved `DependsOn` to top-level of each resource |
| `UnicodeEncodeError` on Windows | `seed_dynamodb.py` used `✓` (U+2713) which Windows `cp1252` terminal cannot encode | Replaced with ASCII `[OK]` |
| `sam build` not finding template | SAM defaults to `template.yml` in project root; file is at `infrastructure/template.yaml` | Always run with `-t infrastructure/template.yaml` flag |
| `aws` not found in PowerShell | AWS CLI installed to user Python Scripts dir not in system PATH | Add `$env:Path += ";C:\Users\avikv\AppData\Roaming\Python\Python313\Scripts"` before every session |

---

## 👥 Contributors

| Student | Branch | Contribution |
|---------|--------|--------------|
| Student 1 | `feature1` | Literature survey, research gap analysis, dashboard UI prototype, Phase I documentation |
| Student 2 (Avik) | `feature2` | Full AWS cloud infrastructure (SAM/CloudFormation), all Lambda functions, DynamoDB schema, API Gateway (REST + WebSocket), Cognito, SNS, IoT Core, S3 hosting, edge server, seed scripts, CI/CD git workflow |
| Student 3 | `feature3` | ML models, federated learning algorithm, dataset preprocessing |

---

## 📄 Phase I Documentation

| Section | File |
|---------|------|
| Abstract | `docs/Abstract.md` |
| Literature Survey | `docs/student1/Literature_Survey_Student1.md` |
| Research Gap | `docs/student1/Research_Gap_Student1.md` |
| Dashboard Design Notes | `docs/student1/Dashboard_Design_Notes.md` |
| Project Objectives | `docs/Objectives.md` |
| Novelty Summary | `docs/Novelty.md` |
| Dataset Details | `docs/Dataset_Details.md` |
| AWS Services Planning | `docs/AWS_Services_Planning.md` |
| Workflow & Evaluation | `docs/Workflow_and_Evaluation.md` |
| Architecture Diagrams | `architecture/` |
| Phase I Presentation | `presentation/Phase1_Presentation_Outline.md` |
