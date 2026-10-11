# Phase 1 Review Outline (10 Slides)
## Cloud Energy Consumption Prediction Framework for Smart University Campuses (AWS)

Format per slide: **Key message**, **Content**, **Visual**, **Say**.

---

### Slide 1: Title and one-line pitch
- **Key message:** A cloud-native AWS pipeline that forecasts campus energy demand and automatically recommends cost-aware control actions.
- **Content:** Title, name (Aaditya Chourasia, 24BIT0556), course, guide, date, repo link
- **Visual:** Campus building, cloud and forecast curve icons
- **Say:** "We turn smart-meter and occupancy data into forecasts and actions that cut peak demand."

### Slide 2: Problem and motivation
- **Key message:** Campus load changes constantly, but most buildings still run on fixed schedules.
- **Content:**
  - Usage shifts with lecture timetables, occupancy and weather
  - Fixed-schedule building management wastes energy at low occupancy and fails during demand spikes
  - Centralized cloud analytics helps, but streaming raw occupancy data raises privacy and bandwidth concerns
- **Visual:** Daily load curve vs. fixed schedule, with wasted area shaded
- **Say:** The goal is real-time visibility and control with secure handling of data.

### Slide 3: Literature survey at a glance
| Paper | Method | Data | Key takeaway |
|---|---|---|---|
| Singh & Nezami (2026) | GRU + FedAvg + rule/cost controller | Synthetic 120-day campus simulator | Federated 8.7% MAPE vs centralized 8.1%; comm. overhead under 6% of raw telemetry; simulation only |
| Oulefki et al. (2024) | IoT data collection, MTF image transform | Real, University of Sharjah, Jan-Jun 2024, 7 appliances, CC BY 4.0 | Open real data, but only 3 rooms and about 5.5 months |
| Sievers & Blank (2023) | Transformer vs LSTM vs CNN, clustered FedAvg (k=6) | 33 KIT smart meters, hourly, 2019-2021 | Transformer matches LSTM with about 48% less training time; FL gain about 1%, up to about 3% |
| Madsen et al. (2024) | Zigbee2MQTT edge gateway | Real 5-day pilot, 10 sensors | Gateway hardware 145 EUR; only edge tier tested |
| Du et al. (2023) | FL-LSTM + Consensus+Innovations optimization | NREL EULP, 125 buildings (synthetic) | FL forecasts improve downstream optimization, up to 8x better price accuracy for low-data community |
- **Visual:** The table above, trimmed to 3 columns for the slide
- **Say:** Five papers cover forecasting, federation, ingestion hardware and control.

### Slide 4: Research gap
- **Key message:** Real data, federated learning and live control have never been combined and deployed.
- **Content:**
  - Real-data studies stay single-room or single-building (Oulefki, Madsen)
  - Federated studies stay synthetic or simulated on one machine (Singh & Nezami, Du, Sievers & Blank)
  - Cloud and fog tiers are described but rarely implemented
  - Security and security-aware client authentication are barely addressed
  - Forecast, control and alerting are seldom shown as one deployed pipeline
- **Visual:** Venn diagram: Real data / Federated learning / Deployed control loop, with the gap in the centre
- **Say:** Our project targets the deployed, end-to-end part of that gap for a single institution.

### Slide 5: Objectives and novelty
- **Objectives (from the project plan):**
  1. Build an IoT ingestion pipeline on AWS IoT Core for meter, temperature and occupancy data
  2. Train a SageMaker forecasting model with target MAPE under 10%
  3. Reduce simulated/test peak demand by at least 15% using tariff-aware load scheduling
  4. Provide role-based access with Cognito and IAM
- **Novelty:**
  - Fully cloud-native serverless pipeline (IoT Core, Lambda, SageMaker) instead of on-premise edge/federated
  - Event-driven design: IoT data triggers Lambda for real-time preprocessing, not batch-only aggregation
  - Real-time SNS alerts for peak-demand and anomaly events
- **Visual:** Four objective icons with measurable targets (MAPE < 10%, peak -15%)

### Slide 6: Proposed AWS architecture
- **Key message:** One event-driven flow from sensor to dashboard and control action.
- **Content:**
  - Ingest: smart meters and sensors to AWS IoT Core
  - Process: Lambda preprocessing to S3 (raw) and RDS/Aurora (structured)
  - Learn: SageMaker training and inference
  - Act: control policy engine (runs every 15 minutes) to building actions and alerts
  - Serve: API Gateway + Cognito to dashboard (QuickSight)
  - Operate: CloudWatch (health, logs), SNS (alerts), IAM (permissions)
- **Visual:** Diagram from `Architecture_Diagrams.md` (diagram 1)
- **Say:** Walk left to right: data in, forecast, decision, action, visibility.

### Slide 7: Data and forecasting plan
- **Key message:** Public real data for validation, strict time-ordered evaluation.
- **Content:**
  - Candidate data: University of Sharjah IoT dataset (Zenodo, DOI 10.5281/zenodo.12750891, CC BY 4.0) for real ground truth; [TODO: add a public smart-meter dataset for campus-scale load, since KIT data is not public]
  - Features: load, occupancy, temperature/humidity, cyclic hour/weekday, academic timetable and holidays
  - Preprocessing: timestamp alignment, imputation, outlier removal, scaling (as in the surveyed papers)
  - Split: chronological 70/20/10 with no shuffling, to avoid leakage
  - Models: [TODO: e.g., seasonal-naive, LSTM/GRU, Transformer] on SageMaker; success target MAPE under 10%
- **Visual:** Timeline of train / validation / test blocks
- **Say:** Literature shows 8.1% to 8.7% MAPE is achievable, so under 10% is a realistic target.

### Slide 8: Control layer and alerting
- **Key message:** Forecasts are only useful if they trigger action.
- **Content:**
  - Rule-and-cost-based controller runs every 15 minutes
  - Actions: adjust HVAC set points, dim lights, defer non-critical loads in peak-tariff windows
  - Comfort constraints differ per room type (classroom, lab, hostel, admin)
  - SNS sends alerts for peak-demand events and anomalies
  - Graceful fallback to local rules if cloud is unreachable [TODO: confirm in your design]
- **Visual:** Control loop: forecast, tariff check, rule engine, action, feedback (diagram 3)

### Slide 9: Security, monitoring and evaluation
- **Key message:** Secure by design, measured against clear targets.
- **Content:**
  - Security: Cognito login, IAM least privilege, encryption in transit and at rest [TODO: KMS], private networking [TODO]
  - Monitoring: CloudWatch metrics and logs, SNS alarms
  - Evaluation metrics: MAPE and RMSE (target MAPE < 10%), peak demand reduction (target 15%), alert latency, cost per month on AWS [TODO]
  - Comparison: fixed schedule baseline vs. forecast-driven control
- **Visual:** Metric scorecard table with target and `[TODO]` actual columns

### Slide 10: Status, limitations, roadmap and conclusion
- **Status:** [TODO: mark each as Done / In progress / Planned] ingestion, storage, forecasting model, control engine, dashboard, security
- **Limitations:** Single-institution scope; peak-reduction claim will be validated in simulation/test, not a live building; no renewable or battery integration yet; federated learning deliberately left out of the first version
- **Roadmap:** Extend to more building types over a full year; add anomaly detection before model retraining; optional federated extension for multi-campus setups
- **Conclusion:** A deployable, secure, cloud-native pipeline that closes the loop from data to forecast to action.
- **Visual:** Roadmap strip plus "Questions?" with repo QR code
