# Phase I Presentation Outline

## Federated Campus Energy Cloud

**Subtitle:** Privacy-Preserving Energy-Demand Forecasting and Flexible-Load Scheduling for Smart University Campuses

---

## Slide structure

### Slide 1 — Title

- Project title and subtitle
- Team member names
- Academic year and submission date

### Slide 2 — Problem statement

- University campuses face rising electricity demand, operating cost and grid pressure
- Centralising smart-meter data creates privacy, bandwidth and governance risks
- New facilities lack historical data for accurate local forecasting

### Slide 3 — Research motivation

- Summary of 5+ reviewed papers (per student assignment)
- Common gap: forecasting, privacy and scheduling are evaluated separately
- No complete production-oriented closed loop demonstrated in literature

### Slide 4 — Proposed solution overview

- Federated learning keeps raw telemetry at the building
- Gaussian differential privacy + pairwise secure aggregation protect model updates
- AWS-managed serverless pipeline: IoT Core → Lambda → SageMaker → S3
- Tariff-aware optimisation schedules HVAC, EV and battery loads

### Slide 5 — System architecture

- Reference: `architecture/System_Architecture.svg`
- End-to-end flow: sensors → Greengrass edge → IoT Core → Lambda → SageMaker → S3 → optimiser → dashboard

### Slide 6 — AWS service mapping

- Reference: `architecture/AWS_Architecture.svg`
- One slide per service tier: ingestion, compute, storage, access, monitoring

### Slide 7 — Dataset details

- Building Data Genome Project 2: 1,570 buildings, 53.6 M records
- ASHRAE GEPIII, Smart* Home, UCI Appliances datasets
- Preprocessing: deduplication, resampling, imputation, federated client partitioning

### Slide 8 — Novelty highlights

- Closed-loop control (forecast → schedule → action)
- Dual privacy layer (local DP + secure aggregation)
- Adaptive client weighting and clustering
- Cold-start onboarding via transfer fine-tuning
- Manager-facing dashboard with demand, alerts and savings

### Slide 9 — Student 1: Literature survey (Papers 1–5)

- Table summary of 5 papers: method, dataset, advantages, limitations
- Identified independent research gap per paper
- Shared conclusion: need for an integrated AWS closed-loop deployment

### Slide 10 — Student 1: Dashboard prototype demo

- Screenshot / live demo of `src/frontend/index.html`
- Sections: KPI strip, demand forecast chart, optimisation schedule, federation table, privacy meters
- Accessibility and information-hierarchy design rationale

### Slide 11 — Evaluation plan

| Metric | Target |
|---|---|
| Peak demand reduction | ≥ 20% vs. unscheduled baseline |
| Forecasting CV-RMSE | < 25% (cold start) |
| Privacy budget | ε ≤ 2.0 per round |
| Update success rate | Monitor in CloudWatch every round |

### Slide 12 — Project timeline (Phase II)

- Month 1: dataset ingestion, edge preprocessing pipeline
- Month 2: federated training loop and privacy implementation
- Month 3: SageMaker aggregation and S3 integration
- Month 4: optimisation function and tariff schedule
- Month 5: dashboard AWS integration and end-to-end testing
- Month 6: evaluation, report writing and final presentation

### Slide 13 — References

- Wen et al. (2023), Sarmento et al. (2024), Li et al. (2023), Rajule et al. (2025), Ma et al. (2026)
- Building Data Genome Project 2 (BUS Lab)
- AWS documentation references

### Slide 14 — Q&A

- Prepared question set:
  - How is differential privacy budget consumed across rounds?
  - How does quality-weighted aggregation differ from FedAvg?
  - What happens when a client fails to submit an update?
  - How is the optimisation function guaranteed to respect comfort constraints?

---

## Presentation notes

- Target duration: 15 minutes + 5 minutes Q&A
- All architecture diagrams should reference the SVG source files in `architecture/`
- Dashboard demo should be run locally: `python3 -m http.server 8000` → `http://localhost:8000/src/frontend/`
- Mark all chart and table values as simulated during Phase I
