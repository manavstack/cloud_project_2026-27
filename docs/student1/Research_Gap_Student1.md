# Research Gap Analysis - Student 1

## Problem

University campuses need short-term electricity forecasts to avoid expensive demand peaks. Centralising high-frequency meter, occupancy and environmental data creates privacy, bandwidth and governance concerns; independent local models lose the benefit of shared learning.

## Identified gap

The reviewed papers do not demonstrate a complete production-oriented path from protected, non-IID edge learning to tariff-aware building control. There is insufficient evidence for differential privacy and secure aggregation being assessed against forecast and control quality, adaptive aggregation when campus behaviour shifts, cold-start learning measured by cost, and AWS identity, event handling, monitoring and dashboard visibility around the workflow.

## Proposed improvement

Greengrass clients train locally, add Gaussian privacy noise and send protected updates through IoT Core. Lambda validates each update; SageMaker performs quality-weighted aggregation; the global checkpoint is stored in S3; and a Lambda optimisation function produces a 15-minute HVAC/EV schedule from predicted load and time-of-use tariffs. DynamoDB records participant and tariff metadata, while Cognito, IAM, CloudWatch, SNS and QuickSight provide secure operations.

## Measurable evaluation

- Target at least 20% peak-demand reduction against an unscheduled baseline.
- Compare forecasting error and cost savings across privacy budgets.
- Measure cold-start CV-RMSE and time required to fine-tune a new facility.
- Track aggregation success rate, update latency and protected-update size.
