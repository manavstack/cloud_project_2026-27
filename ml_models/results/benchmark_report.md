# 📊 Multi-Dataset Machine Learning Benchmark Report

**Champion Model**: `Deep_MLP_Neural_Network`
**Integrated Partitions**: 4 datasets integrated

## 1. Comparative Performance Matrix

| Model Architecture | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Log Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic_Regression_L2** | 0.8563 | 0.8388 | 0.8111 | **0.8247** | 0.9305 | 0.3350 |
| **Deep_MLP_Neural_Network** | 0.9163 | 0.8780 | 0.9280 | **0.9023** | 0.9818 | 0.3234 |
| **Random_Forest_Ensemble** | 0.8582 | 0.8571 | 0.7916 | **0.8231** | 0.9355 | 0.3649 |

## 2. Champion Model Confusion Matrix

| Actual \ Predicted | Predicted Negative (0) | Predicted Positive (1) |
| :--- | :---: | :---: |
| **Actual Negative (0)** | **TN = 848** | FP = 86 |
| **Actual Positive (1)** | FN = 48 | **TP = 619** |

## 3. Data Integration & Production Notes

- **Multi-Source Fusion**: Trained across unified multi-channel telemetry features combining all four dataset partitions.
- **Data Leakage Prevention**: Train/Test stratification applied strictly prior to feature standardization.
- **Generalization Score**: Reached test F1-score of **0.9023** and ROC-AUC of **0.9818**.
