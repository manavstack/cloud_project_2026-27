# Likely Reviewer Questions

**1. The reference paper uses federated learning. Why is yours centralized?**
The target is a single institution, where one secure cloud pipeline is simpler to deploy. Singh & Nezami's federated model was also slightly less accurate than centralized (8.7% vs 8.1% MAPE). Federation stays as future work for multi-campus use.

**2. What about the privacy concern you raised?**
Data stays inside the institution's AWS account, access is role-based (Cognito, IAM), and no personal data is collected; occupancy is aggregated sensor state. [TODO: add encryption details you implement]

**3. Where does your real data come from?**
The University of Sharjah dataset (open, CC BY 4.0) gives real appliance and environmental data; it is small (about 5.5 months, 3 rooms). [TODO: state what you actually use for campus-scale training]

**4. Is the 10% MAPE target realistic?**
Surveyed work reports 8.1% to 8.7% on simulated campus data. Real data is noisier, so we treat 10% as the target and report actual results. [TODO]

**5. How will you prove 15% peak reduction without a live campus?**
By simulated/test replay: apply the controller to historical or simulated load with tariff windows and compare against the fixed-schedule baseline.

**6. Why serverless and event-driven?**
Lambda scales with sensor volume and removes server management; IoT Core rules trigger real-time preprocessing instead of waiting for batch aggregation.

**7. What if the cloud connection fails?**
Surveyed design falls back to local rules. [TODO: confirm whether your design includes this]

**8. What are the main limitations?**
Single institution, limited real data, no battery/renewable integration, controller validated offline.

**9. Why RDS/Aurora and S3 both?**
S3 keeps immutable raw data; the relational store holds cleaned, queryable data for dashboards and training.

**10. What would you do next?**
More building types over a full year, anomaly detection before retraining, optional federated extension, cost analysis.
