# Federated Campus Energy Cloud

An AWS-oriented prototype for privacy-preserving energy-demand forecasting and flexible-load scheduling across smart university campuses.

## Student 1 contribution

- Literature survey and original research-gap analysis for Papers 1-5
- Interactive facility-operations dashboard prototype (see `src/frontend/`)
- Frontend information architecture and accessibility baseline
- Dashboard design notes and information-hierarchy rationale

See `docs/` for all Phase I sections, `docs/student1/` for Student 1's assigned research, and the runnable dashboard in `src/frontend/`.

## Run locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000/src/frontend/
```

## Proposed stack

AWS IoT Core and Greengrass ingest edge telemetry; Lambda validates events and runs optimisation; S3 stores model artefacts; DynamoDB stores metadata and tariffs; SageMaker aggregates federated updates; Cognito/API Gateway protect dashboard access; CloudWatch and SNS provide operations monitoring and alerts.

## Phase I sections

| Section | Location |
|---|---|
| Abstract | docs/Abstract.md |
| Literature survey and individual research gap | docs/student1/Literature_Survey_Student1.md |
| Research gap analysis | docs/student1/Research_Gap_Student1.md |
| Dashboard design notes | docs/student1/Dashboard_Design_Notes.md |
| Project objectives | docs/Objectives.md |
| Novelty summary | docs/Novelty.md |
| Dataset details and preprocessing | docs/Dataset_Details.md |
| AWS service planning | docs/AWS_Services_Planning.md |
| Workflow and evaluation plan | docs/Workflow_and_Evaluation.md |
| Mandatory architecture diagrams | architecture/ |
| Phase I presentation outline | presentation/Phase1_Presentation_Outline.md |
