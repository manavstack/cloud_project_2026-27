# Model Layer

`src.train_baselines` evaluates chronology-aware persistence. `src.train_experts` trains one gradient-boosting expert per source. `src.moe.HybridAdaptiveMoE` fits a differentiable softmax gate on prior calibration data and combines it with exponentially weighted expert reliability. The `observe` method is intentionally separate from `predict` to prevent target leakage.
