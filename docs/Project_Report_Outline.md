# Project Report Outline

## Abstract

Smart campuses produce energy time series with different units, cadences, timezones, and asset structures, while data owners may not be able to pool meter records centrally. FEDRA provides source-aware validation and chronological forecasting, plus an experimental federated-learning demonstration. The local FedAvg workflow trains an interpretable time-of-week profile independently on eligible IIT Bombay apartment, IIIT-Delhi building, and Valahia building/year/vector datasets. Each client normalizes its target using training-only observations, retains raw data and absolute scale locally, and shares model parameters for sample-count-weighted aggregation. Per-client evaluation uses a later chronological holdout. La Trobe is withheld until its unit/timezone are verified, and the small University of Twente extracts are withheld until more observations are available.

The shared five-parameter model represents a normalized relative profile, not an absolute energy forecast. The current run is a single-machine simulation: it demonstrates the client/aggregation boundary, not communication among campuses, secure aggregation, differential privacy, or production deployment. The PostgreSQL dashboard remains a separate single-contract gradient-boosting experiment with physical-unit metrics. Future work is to establish authenticated campus clients, secure parameter aggregation, validate source contracts, and evaluate more expressive source-specific experts before proposing the Hybrid Adaptive Mixture-of-Experts model or AWS deployment.

## Required technical sections

1. Problem statement and measurable objectives.
2. Novelty: source-aware expert specialization, gradient gating, and post-observation reliability updates.
3. Dataset details and provenance policy.
4. AWS cloud and complete-system architecture diagrams.
5. Canonical schema, security, and credentials policy.
6. Chronological validation, results, limitations, and privacy boundary of the FedAvg simulation.

Literature survey and individual research-gap documents are intentionally outside this Feature 1 implementation scope.
