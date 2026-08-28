# Literature Survey - Student 1 (Papers 1-5)

This review covers the first five papers assigned to Student 1. The gaps below are the team's interpretation, not copied statements.

| Paper | Method | Dataset | Advantages | Limitations | Independent research gap / possible improvement |
|---|---|---|---|---|---|
| Wen et al. (2023) | Taxonomy of horizontal, vertical and transfer federated learning; secure multiparty computation, differential privacy and homomorphic encryption | Secondary review of more than 160 studies | Broad map of security, communication and non-IID problems | Survey only; no live building or cloud workflow evaluation | Compare privacy mechanisms on the same multi-campus workload, including network jitter, edge hardware limits and AWS operating cost. |
| Sarmento et al. (2024) | CNN-LSTM federated forecasting with TimeGAN augmentation on edge devices | Smart* Home and Building Data Genome Project 2 | Captures temporal patterns with a small edge footprint; tests sparse sampling | Client drift is not adaptively corrected as occupancy and equipment change | Add periodic client clustering and quality-weighted aggregation so the federation adapts when a campus profile changes. |
| Li et al. (2023) | ANN forecasting, pairwise secure aggregation, SHAP and transfer fine-tuning | Building Data Genome Project, 13-office-building subset | Improves cold-start forecasting and protects continuous model weights | Does not connect prediction quality to tariff-aware control | Evaluate whether cold-start transfer learning improves a real flexible-load schedule and energy-cost outcome, not only CV-RMSE. |
| Rajule et al. (2025) | LSTM/GRU forecasting, federated averaging, Gaussian differential privacy and Pyomo linear programming | Synthesised ASHRAE GEPIII and UCI building-energy data | Reports peak reduction, cost savings and low communication overhead | Simulated edge network; no enterprise identity, serverless integration or dashboard | Test privacy-budget choices and scheduling performance together in a secure AWS event-driven deployment. |
| Ma et al. (2026) | FT-ECP federated attention transformer with data adaptation and weighted aggregation | Eastern China office-park dataset | Strong accuracy and lower communication / differential-privacy budget | One regional context; performance falls with small samples and lacks weather-anomaly automation | Validate dynamic weighting across climates, tariffs and campus calendars; add anomaly-aware features and cold-start evaluation. |

## Shared conclusion

Existing work often evaluates forecasting, privacy, or load optimisation separately. The proposed system joins these in an AWS-managed closed loop: edge nodes retain raw telemetry, upload protected model updates, receive an aggregated forecast, and use it to derive a tariff-aware HVAC and EV schedule. The dashboard makes demand, alerts and savings understandable to facility managers.
