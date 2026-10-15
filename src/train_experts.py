"""
train_experts.py
================
Trains 3 specialist models — one per building category:

    academic     → Random Forest Regressor
    residential  → XGBoost Regressor
    others       → Gradient Boosting Regressor

Features are strictly general temporal/cyclic patterns (hour, day_of_week, 
month, is_weekend, cyclic sines/cosines). Building name identity is intentionally
omitted from training so models generalize to any unseen building.

Saved to /app/models/<category>_expert.pkl
"""

import os
import joblib
import numpy as np

from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from db import load_category_data
from features import create_features


# ============================================================
# Config
# ============================================================

MODEL_DIR    = os.getenv("MODEL_DIR", "/app/models")
TEST_SIZE    = 0.2
RANDOM_STATE = 42

# General temporal features (no building identity to ensure unseen building generalization)
FEATURE_COLS = [
    "hour",
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
]

EXPERTS = {
    "academic": RandomForestRegressor(
        n_estimators=200,
        random_state=RANDOM_STATE,
        n_jobs=-1
    ),
    "residential": XGBRegressor(
        n_estimators=200,
        learning_rate=0.05,
        random_state=RANDOM_STATE,
        verbosity=0
    ),
    "others": GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        random_state=RANDOM_STATE
    ),
}


# ============================================================
# Helpers
# ============================================================

def print_metrics(category, y_true, y_pred):
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)

    print(f"  MAE  : {mae:.4f} kWh")
    print(f"  RMSE : {rmse:.4f} kWh")
    print(f"  R²   : {r2:.4f}")

    return {"mae": mae, "rmse": rmse, "r2": r2}


# ============================================================
# Main training loop
# ============================================================

def train_all():

    os.makedirs(MODEL_DIR, exist_ok=True)
    summary = {}

    for category, model in EXPERTS.items():

        print()
        print("=" * 55)
        print(f"  Expert: {category.upper()}")
        print("=" * 55)

        # ── 1. Load from DB ───────────────────────────────
        print(f"  → Loading '{category}' from DB...")
        df = load_category_data(category)
        print(f"  → {len(df)} rows loaded.")

        if df.empty:
            print(f"  ⚠  No data — skipping.")
            continue

        # ── 2. Feature engineering ────────────────────────
        df = create_features(df)

        X = df[FEATURE_COLS]
        y = df["consumption_kwh"].astype(float)

        # ── 3. Train / test split ─────────────────────────
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE
        )
        print(f"  → Train: {len(X_train)}  |  Test: {len(X_test)}")

        # ── 4. Fit ────────────────────────────────────────
        print(f"  → Fitting {model.__class__.__name__}...")
        model.fit(X_train, y_train)

        # ── 5. Evaluate ───────────────────────────────────
        y_pred = model.predict(X_test)
        metrics = print_metrics(category, y_test, y_pred)
        summary[category] = metrics

        # ── 6. Save model ─────────────────────────────────
        model_path = os.path.join(
            MODEL_DIR, f"{category}_expert.pkl"
        )
        joblib.dump(model, model_path)
        print(f"  ✓ Saved → {model_path}")

    # ── Summary ───────────────────────────────────────────
    print()
    print("=" * 55)
    print("  TRAINING COMPLETE — SUMMARY")
    print("=" * 55)
    for cat, m in summary.items():
        print(
            f"  {cat:<15} "
            f"MAE={m['mae']:.3f}  "
            f"RMSE={m['rmse']:.3f}  "
            f"R²={m['r2']:.3f}"
        )
    print()


if __name__ == "__main__":
    train_all()
