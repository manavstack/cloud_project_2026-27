# Phase 1 Review Outline

1. Problem and motivation: heterogeneous campus energy data and privacy-preserving forecasting.
2. Objective: reproducible, per-client local training with a shareable global model.
3. Dataset provenance and eligibility: IIT Bombay, IIIT-Delhi, Valahia, La Trobe, and Twente.
4. Canonical PostgreSQL design, source contracts, and credentials controls.
5. Local workflow: training-only normalization, campus-local time features, chronological holdout.
6. FedAvg: client-local parameter updates, sample-count aggregation, and round-by-round weights.
7. Results panel: active clients, excluded-data rationale, normalized metrics, and global weights.
8. Privacy boundary: raw records remain local; simulation limitations and update leakage risk.
9. Centralized single-contract forecast versus the separate normalized-profile FedAvg experiment.
10. Proposed next steps: multi-host clients, secure aggregation, and only then the Hybrid Adaptive MoE.
