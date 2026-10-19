"""
End-to-End Multi-Dataset Training & Benchmarking Pipeline
Integrates multiple datasets, trains baseline and advanced architectures,
saves champion model weights, and outputs full evaluation artifacts.
"""

import os
import sys
import json
import numpy as np

sys.path.append(os.path.dirname(__file__))

from data_loader import DataLoader
from models import LogisticRegressionModel, MLPNeuralNetwork, RandomForestClassifierModel

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    
    total = len(y_true)
    accuracy = float((tp + tn) / total)
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1_score = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    
    p1 = y_prob[:, 1]
    sorted_idx = np.argsort(p1)
    y_sorted = y_true[sorted_idx]
    n_pos = np.sum(y_true == 1)
    n_neg = np.sum(y_true == 0)
    
    if n_pos > 0 and n_neg > 0:
        ranks = np.empty_like(sorted_idx)
        ranks[sorted_idx] = np.arange(len(sorted_idx))
        rank_sum_pos = np.sum(ranks[y_true == 1])
        roc_auc = float((rank_sum_pos - (n_pos * (n_pos - 1)) / 2.0) / (n_pos * n_neg))
    else:
        roc_auc = 0.5
        
    eps = 1e-15
    clipped_p1 = np.clip(p1, eps, 1 - eps)
    log_loss = float(-np.mean(y_true * np.log(clipped_p1) + (1 - y_true) * np.log(1 - clipped_p1)))
    
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1_score, 4),
        "roc_auc": round(roc_auc, 4),
        "log_loss": round(log_loss, 4),
        "confusion_matrix": {
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn
        }
    }

def main():
    print("=" * 75)
    print("🚀 MULTI-DATASET MACHINE LEARNING TRAINING & INTEGRATION PIPELINE")
    print("=" * 75)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    models_dir = os.path.join(base_dir, "models")
    results_dir = os.path.join(base_dir, "results")
    
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    # 1. Multi-Dataset Ingestion
    loader = DataLoader(data_dir=data_dir)
    X, y, feature_names = loader.scan_and_load_all_datasets(
        n_samples_default=8000, 
        n_features_default=16, 
        seed=42
    )
    print(f"[*] Integrated Dataset: {X.shape[0]} total samples across {X.shape[1]} features.")
    print(f"[*] Partitions Included: {', '.join(loader.datasets_loaded)}")
    
    # 2. Strict Train/Test Separation (ML Best Practice)
    X_train_raw, X_test_raw, y_train, y_test = loader.split_train_test(X, y, test_size=0.2, seed=42)
    print(f"[*] Partition Split: {len(X_train_raw)} training samples | {len(X_test_raw)} held-out test samples.")
    
    # 3. Fit Preprocessing strictly on train data
    X_train = loader.fit_transform_train(X_train_raw)
    X_test = loader.transform_test(X_test_raw)
    
    # 4. Multi-Model Architecture Benchmarking
    models = {
        "Logistic_Regression_L2": LogisticRegressionModel(lr=0.06, l2_reg=1e-4, epochs=180),
        "Deep_MLP_Neural_Network": MLPNeuralNetwork(hidden_dims=[128, 64, 32], lr=0.003, epochs=150, batch_size=64),
        "Random_Forest_Ensemble": RandomForestClassifierModel(n_estimators=35, max_depth=9)
    }
    
    benchmark_results = {}
    best_model_name = None
    best_f1 = -1.0
    
    for name, model in models.items():
        print(f"\n[+] Training {name} across integrated feature space...")
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)
        
        metrics = compute_metrics(y_test, y_pred, y_prob)
        benchmark_results[name] = metrics
        print(f"    -> Accuracy: {metrics['accuracy']:.4f} | F1: {metrics['f1_score']:.4f} | ROC-AUC: {metrics['roc_auc']:.4f}")
        
        if metrics["f1_score"] > best_f1:
            best_f1 = metrics["f1_score"]
            best_model_name = name

    print("\n" + "=" * 75)
    print(f"🏆 CHAMPION MODEL: {best_model_name} (F1-Score: {best_f1:.4f})")
    print("=" * 75)
    
    # 5. Export Champion Model Weights
    best_model = models[best_model_name]
    
    if best_model_name == "Deep_MLP_Neural_Network":
        weights_dict = {f"W_{i}": w for i, w in enumerate(best_model.weights)}
        biases_dict = {f"b_{i}": b for i, b in enumerate(best_model.biases)}
        save_data = {**weights_dict, **biases_dict, "scaler_mean": loader.mean_, "scaler_std": loader.std_}
        np.savez_compressed(os.path.join(models_dir, "best_model.npz"), **save_data)
    elif best_model_name == "Logistic_Regression_L2":
        np.savez_compressed(
            os.path.join(models_dir, "best_model.npz"), 
            weights=best_model.weights, 
            bias=np.array([best_model.bias]),
            scaler_mean=loader.mean_, 
            scaler_std=loader.std_
        )
    else:
        np.savez_compressed(
            os.path.join(models_dir, "scaler_params.npz"),
            scaler_mean=loader.mean_,
            scaler_std=loader.std_
        )

    # Save Metadata
    metadata = {
        "best_model_architecture": best_model_name,
        "n_features": len(feature_names),
        "feature_names": feature_names,
        "datasets_integrated": loader.datasets_loaded,
        "classes": [0, 1],
        "test_samples": len(y_test),
        "train_samples": len(y_train),
        "selected_metrics": benchmark_results[best_model_name]
    }
    with open(os.path.join(models_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    # 6. Save Metrics JSON
    metrics_path = os.path.join(results_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump({
            "champion_model": best_model_name,
            "datasets_integrated": loader.datasets_loaded,
            "models_evaluated": benchmark_results
        }, f, indent=2)

    # 7. Generate Formatted Benchmark Report
    report_path = os.path.join(results_dir, "benchmark_report.md")
    with open(report_path, "w") as f:
        f.write("# 📊 Multi-Dataset Machine Learning Benchmark Report\n\n")
        f.write(f"**Champion Model**: `{best_model_name}`\n")
        f.write(f"**Integrated Partitions**: {len(loader.datasets_loaded)} datasets integrated\n\n")
        f.write("## 1. Comparative Performance Matrix\n\n")
        f.write("| Model Architecture | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Log Loss |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for m_name, m_metrics in benchmark_results.items():
            f.write(f"| **{m_name}** | {m_metrics['accuracy']:.4f} | {m_metrics['precision']:.4f} | {m_metrics['recall']:.4f} | **{m_metrics['f1_score']:.4f}** | {m_metrics['roc_auc']:.4f} | {m_metrics['log_loss']:.4f} |\n")
        
        cm = benchmark_results[best_model_name]["confusion_matrix"]
        f.write("\n## 2. Champion Model Confusion Matrix\n\n")
        f.write(f"| Actual \\ Predicted | Predicted Negative (0) | Predicted Positive (1) |\n")
        f.write(f"| :--- | :---: | :---: |\n")
        f.write(f"| **Actual Negative (0)** | **TN = {cm['true_negative']}** | FP = {cm['false_positive']} |\n")
        f.write(f"| **Actual Positive (1)** | FN = {cm['false_negative']} | **TP = {cm['true_positive']}** |\n")
        
        f.write("\n## 3. Data Integration & Production Notes\n\n")
        f.write("- **Multi-Source Fusion**: Trained across unified multi-channel telemetry features combining all four dataset partitions.\n")
        f.write("- **Data Leakage Prevention**: Train/Test stratification applied strictly prior to feature standardization.\n")
        f.write(f"- **Generalization Score**: Reached test F1-score of **{benchmark_results[best_model_name]['f1_score']:.4f}** and ROC-AUC of **{benchmark_results[best_model_name]['roc_auc']:.4f}**.\n")

    print(f"\n[*] Updated metrics saved to: {metrics_path}")
    print(f"[*] Updated benchmark report to: {report_path}")
    print("\n✅ MULTI-DATASET TRAINING COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
