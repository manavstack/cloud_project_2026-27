"""
train.py
--------
Trains an XGBoost regressor to forecast next-15-minute building power load
(target_power_kw), per the Buildable MVP Plan (Section 4, Week 2 - Forecasting).

Target: MAPE < 10% (matches the project's forecasting accuracy goal).

Outputs:
    src/ml_model/model.pkl                     - trained model (joblib)
    src/ml_model/feature_columns.json          - feature column order for predict.py
    results/accuracy.xlsx                      - MAPE / MAE / RMSE per split
    results/graphs/actual_vs_predicted.png
    results/graphs/feature_importance.png
    results/graphs/error_distribution.png
"""

import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error, mean_squared_error

PROCESSED_PATH = "dataset/processed/energy_readings_features.csv"
MODEL_PATH = "src/ml_model/model.pkl"
FEATURE_COLS_PATH = "src/ml_model/feature_columns.json"
ACCURACY_XLSX = "results/accuracy.xlsx"

NON_FEATURE_COLS = ["timestamp", "target_power_kw"]


def time_based_split(df, train_frac=0.7, val_frac=0.15):
    """Split chronologically per building to avoid leakage (no shuffling)."""
    df = df.sort_values("timestamp")
    n = len(df)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]


def evaluate(y_true, y_pred):
    return {
        "MAPE_%": round(mean_absolute_percentage_error(y_true, y_pred) * 100, 3),
        "MAE_kW": round(mean_absolute_error(y_true, y_pred), 3),
        "RMSE_kW": round(np.sqrt(mean_squared_error(y_true, y_pred)), 3),
    }


def main():
    df = pd.read_csv(PROCESSED_PATH, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    train_df, val_df, test_df = time_based_split(df)

    X_train, y_train = train_df[feature_cols], train_df["target_power_kw"]
    X_val, y_val = val_df[feature_cols], val_df["target_power_kw"]
    X_test, y_test = test_df[feature_cols], test_df["target_power_kw"]

    model = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="mae",
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    results = {
        "train": evaluate(y_train, model.predict(X_train)),
        "validation": evaluate(y_val, model.predict(X_val)),
        "test": evaluate(y_test, model.predict(X_test)),
    }

    print("Evaluation results:")
    for split, metrics in results.items():
        print(f"  {split:10s} -> {metrics}")

    # --- save model + feature order ---
    joblib.dump(model, MODEL_PATH)
    with open(FEATURE_COLS_PATH, "w") as f:
        json.dump(feature_cols, f, indent=2)

    # --- results/accuracy.xlsx ---
    acc_df = pd.DataFrame(results).T.reset_index().rename(columns={"index": "split"})
    acc_df.to_excel(ACCURACY_XLSX, index=False)

    # --- graphs ---
    y_test_pred = model.predict(X_test)

    plt.figure(figsize=(10, 4))
    plt.plot(y_test.values[:300], label="Actual", linewidth=1.5)
    plt.plot(y_test_pred[:300], label="Predicted", linewidth=1.2, alpha=0.8)
    plt.title("Actual vs Predicted Power Load (test set, first 300 points)")
    plt.xlabel("Time step")
    plt.ylabel("Power (kW)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("results/graphs/actual_vs_predicted.png", dpi=150)
    plt.close()

    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=True).tail(12)
    plt.figure(figsize=(8, 6))
    importances.plot(kind="barh")
    plt.title("Top 12 Feature Importances (XGBoost)")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig("results/graphs/feature_importance.png", dpi=150)
    plt.close()

    errors = y_test.values - y_test_pred
    plt.figure(figsize=(7, 4))
    plt.hist(errors, bins=40, color="#4C72B0", edgecolor="white")
    plt.title("Prediction Error Distribution (test set)")
    plt.xlabel("Actual - Predicted (kW)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig("results/graphs/error_distribution.png", dpi=150)
    plt.close()

    print(f"\nSaved model -> {MODEL_PATH}")
    print(f"Saved accuracy report -> {ACCURACY_XLSX}")
    print("Saved graphs -> results/graphs/")


if __name__ == "__main__":
    main()
