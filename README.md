# Federated Campus Energy Cloud

An AWS-oriented prototype for privacy-preserving energy-demand forecasting and flexible-load scheduling across smart university campuses.

## Student 1 contribution

- Literature survey and original research-gap analysis for Papers 1-5
- Interactive facility-operations dashboard prototype
- Frontend information architecture and accessibility baseline

See docs/ for all Phase I sections, docs/student1/ for Student 1's assigned research, and the runnable dashboard in src/frontend/.

## Run locally

Run `python3 -m http.server 8000` in this repository, then open `http://localhost:8000/src/frontend/`.

## Proposed stack

AWS IoT Core and Greengrass ingest edge telemetry; Lambda validates events and runs optimisation; S3 stores model artefacts; DynamoDB stores metadata and tariffs; SageMaker aggregates federated updates; Cognito/API Gateway protect dashboard access; CloudWatch and SNS provide operations monitoring and alerts.

## Phase I sections

| Section | Location |
|---|---|
| Abstract | docs/Abstract.md |
| Literature survey and individual research gap | docs/student1/ |
| Project objectives | docs/Objectives.md |
| Novelty summary | docs/Novelty.md |
| Dataset details and preprocessing | docs/Dataset_Details.md |
| AWS service planning | docs/AWS_Services_Planning.md |
| Workflow and evaluation plan | docs/Workflow_and_Evaluation.md |
| Mandatory architecture diagrams | architecture/ |
