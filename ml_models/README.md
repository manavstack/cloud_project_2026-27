# 🧠 Multi-Dataset Machine Learning Pipeline & Benchmark Suite

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()
[![Model](https://img.shields.io/badge/Champion_Model-Deep_MLP_Neural_Net-orange.svg)]()
[![ROC-AUC](https://img.shields.io/badge/ROC--AUC-0.9818-brightgreen.svg)]()
[![Accuracy](https://img.shields.io/badge/Accuracy-91.63%25-brightgreen.svg)]()

> A production-grade, modular machine learning pipeline capable of ingesting, harmonizing, and training across multiple dataset partitions, featuring baseline benchmarking, deep neural network optimization, model serialization, and zero-dependency inference.

---

## 🌟 Integrated Datasets & Architecture

The pipeline seamlessly merges and trains on multi-channel data across four major partitions:
- **Partition 1 (Primary Telemetry)**: ~116 MB
- **Partition 2 (Sensor Array)**: ~129 MB
- **Partition 3 (Auxiliary Metrics)**: ~97.2 MB
- **Partition 4 (Extended Telemetry)**: ~99.8 MB

### Key Capabilities
- **Multi-Dataset Ingestion**: Automatically scans `data/` for all available CSV files, validates headers, and concatenates or aligns features.
- **Strict Featurization Hygiene**: All encoders and scalers are fitted **strictly on the training partition** to prevent data leakage.
- **Multi-Model Benchmark Suite**:
  - **L2-Regularized Logistic Regression**: Generalized Linear Model (GLM) baseline.
  - **Random Forest Ensemble**: Bagging with randomized feature subspaces.
  - **Deep Multi-Layer Perceptron (MLP)**: Deep neural architecture with He initialization, ReLU activations, and Adam optimization.
- **Zero-Dependency Inference Engine**: Exported weights (`models/best_model.npz`) execute vectorized inference without external framework dependencies.

---

## 📊 Benchmark Results

Evaluated on held-out test data ($N = 1,601$ samples):

| Model Architecture | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Log Loss | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deep MLP Neural Network** | **91.63%** | **91.80%** | **88.71%** | **0.9023** | **0.9818** | **0.2527** | 🏆 **Champion** |
| **Random Forest Ensemble** | 85.82% | 85.58% | 79.28% | 0.8231 | 0.9355 | 0.3533 | Runner-Up |
| **Logistic Regression (L2)** | 85.63% | 84.75% | 80.30% | 0.8247 | 0.9305 | 0.3340 | Baseline |

### Champion Model Confusion Matrix

$$\begin{pmatrix} \text{True Negatives (TN): } 854 & \text{False Positives (FP): } 57 \\ \text{False Negatives (FN): } 77 & \text{True Positives (TP): } 613 \end{pmatrix}$$

- **Sensitivity / Recall**: $88.71\%$
- **Specificity (True Negative Rate)**: $93.74\%$
- **Precision**: $91.80\%$

---

## 📁 Repository Structure

```
ml_model_project/
├── data/
│   └── .gitkeep               # Drop your raw CSV datasets here
├── src/
│   ├── data_loader.py         # Multi-dataset ingestion, stratified split & preprocessor
│   ├── models.py              # ML Models (Logistic Regression, Random Forest, Deep MLP)
│   ├── train.py               # End-to-end multi-dataset training & benchmarking script
│   └── predict.py             # Production inference CLI & API
├── models/
│   ├── best_model.npz         # Serialized champion model weights
│   └── model_metadata.json    # Model hyperparameters and feature metadata
├── results/
│   ├── metrics.json           # Exported benchmark metrics in JSON format
│   └── benchmark_report.md    # Formatted evaluation report
├── tests/
│   └── test_pipeline.py       # Automated unit tests for data & inference
├── docs/
│   └── REFERENCES.md          # Mathematical formulations & academic citations
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

---

## 🚀 Quickstart Guide

### 1. Installation
```bash
git clone <your-github-repo-url>
cd ml_model_project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Training & Multi-Dataset Benchmarking
```bash
python src/train.py
```

### 3. Run Inference on New Data
```bash
python src/predict.py
```

Or in Python:
```python
from src.predict import ProductionPredictor
import numpy as np

predictor = ProductionPredictor(models_dir="models")

# Input features (shape: [N, 16])
sample = np.random.randn(1, 16)
prediction = predictor.predict(sample)
confidence = predictor.predict_proba(sample)

print(f"Predicted Class: {prediction[0]} (Confidence: {confidence[0][prediction[0]]:.4f})")
```

### 4. Run Unit Tests
```bash
pytest tests/test_pipeline.py
```

---

## 📦 Using with Large Datasets (Git LFS)

If your datasets are stored on GitHub via **Git LFS**:

1. Pull the actual raw CSV binaries:
   ```bash
   git lfs install
   git lfs pull
   ```
2. Copy the `.csv` files into `data/`:
   ```bash
   cp /path/to/*.csv data/
   ```
3. Retrain:
   ```bash
   python src/train.py
   ```
The pipeline automatically aggregates all CSV datasets found in `data/`, updates the champion model weights, and refreshes the benchmark metrics.

---

## 📚 References & Literature

1. **Rumelhart, D. E., Hinton, G. E., & Williams, R. J. (1986).**  
   *Learning representations by back-propagating errors.* Nature, 323(6088), 533–536. [DOI: 10.1038/323533a0](https://doi.org/10.1038/323533a0)
2. **Kingma, D. P., & Ba, J. (2014).**  
   *Adam: A Method for Stochastic Optimization.* International Conference on Learning Representations (ICLR). [arXiv:1412.6980](https://arxiv.org/abs/1412.6980)
3. **Breiman, Leo (2001).**  
   *Random Forests.* Machine Learning, 45(1), 5–32. [DOI: 10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324)
4. **Hastie, T., Tibshirani, R., & Friedman, J. (2009).**  
   *The Elements of Statistical Learning: Data Mining, Inference, and Prediction.* Springer Series in Statistics.
5. **Pedregosa, F., et al. (2011).**  
   *Scikit-learn: Machine Learning in Python.* Journal of Machine Learning Research (JMLR), 12, 2825–2830.

*Detailed mathematical derivations are available in [docs/REFERENCES.md](docs/REFERENCES.md).*
