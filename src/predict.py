"""
predict.py
==========
Main Production Inference Module for FEDRA.
Runs pure inference using the 3 frozen expert models combined with
the latest dynamically calibrated 3x3 MoE weight matrix.

Key Features:
  - Automatically loads the latest learned weights from models/hybrid_moe_state.json
    (falls back to unbiased 1/3 equal weights if not calibrated yet).
  - Selects the specific target category's learned row [w_cA, w_cR, w_cO].
  - Can be run interactively (prompting for time & category) or with CLI arguments.
  - Pure inference: DOES NOT ask for actual value and DOES NOT update weights.

Usage Examples:
  # Interactive mode:
  python src/predict.py

  # Direct CLI mode:
  python src/predict.py --category residential --time "2026-10-15 14:00:00"

  run command : docker run -it --rm -v "${PWD}/models:/app/models" -v "${PWD}/src:/app/src" cloud_project_2026-27-ml 
  python src/predict.py
  
"""

import os
import sys
import json
import argparse
import joblib
import numpy as np
import pandas as pd

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from features import create_features


# ============================================================
# Configuration
# ============================================================

if os.path.exists("/app/models"):
    MODEL_DIR = "/app/models"
else:
    MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

STATE_FILE = os.path.join(MODEL_DIR, "hybrid_moe_state.json")

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

CATEGORIES = ["academic", "residential", "others"]


# ============================================================
# Weight Matrix Loader
# ============================================================

def softmax(logits_dict: dict) -> dict:
    """Computes stable softmax over dictionary of logits."""
    keys = list(logits_dict.keys())
    values = np.array([logits_dict[k] for k in keys], dtype=float)
    shifted = values - np.max(values)
    exp_vals = np.exp(shifted)
    probs = exp_vals / np.sum(exp_vals)
    return {k: float(p) for k, p in zip(keys, probs)}


def load_latest_weights(category: str) -> tuple:
    """
    Loads the latest calibrated weights for the specified target category.
    Returns:
        hybrid_w: dict of final normalized weights {expert: weight}
        gate_g: dict of learned gate priors
        hedge_h: dict of hedge reliability factors
        source_desc: string indicating where weights were loaded from
    """
    num_experts = len(CATEGORIES)
    default_state = {
        "z": {exp: 0.0 for exp in CATEGORIES},
        "h": {exp: 1.0 / num_experts for exp in CATEGORIES},
    }

    state = None
    source_desc = "Default Equal Weights (33.3%, 33.3%, 33.3%)"

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                saved = json.load(f)
            if category in saved:
                state = saved[category]
                source_desc = "Latest Dynamic Weights (from models/hybrid_moe_state.json)"
        except Exception:
            state = None

    if state is None:
        state = default_state

    # 1. Gate weights g from logits z
    gate_g = softmax(state.get("z", default_state["z"]))

    # 2. Hedge reliability weights h
    hedge_h = state.get("h", default_state["h"]).copy()

    # 3. Hybrid combiner: w_i = (g_i * h_i) / sum(g_j * h_j)
    unnorm_w = {exp: gate_g[exp] * hedge_h[exp] for exp in CATEGORIES}
    sum_w = sum(unnorm_w.values())
    if sum_w <= 0:
        hybrid_w = {exp: 1.0 / num_experts for exp in CATEGORIES}
    else:
        hybrid_w = {exp: unnorm_w[exp] / sum_w for exp in CATEGORIES}

    return hybrid_w, gate_g, hedge_h, source_desc


# ============================================================
# Inference
# ============================================================

def load_models() -> dict:
    """Loads all 3 frozen expert models."""
    models = {}
    for cat in CATEGORIES:
        path = os.path.join(MODEL_DIR, f"{cat}_expert.pkl")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file '{path}' not found. Please train models first.")
        models[cat] = joblib.load(path)
    return models


def predict_raw_experts(models: dict, timestamp_str: str) -> dict:
    """Runs raw inference across all 3 frozen experts for a timestamp."""
    df = pd.DataFrame([{"reading_time": timestamp_str}])
    df = create_features(df)
    X = df[FEATURE_COLS]
    return {cat: float(models[cat].predict(X)[0]) for cat in CATEGORIES}


def run_prediction(category: str, timestamp_str: str, models: dict = None) -> dict:
    """
    Executes pure MoE prediction for target category using latest calibrated weights.
    """
    category = category.lower()
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {CATEGORIES}")

    if models is None:
        models = load_models()

    # 1. Get raw expert predictions
    raw_preds = predict_raw_experts(models, timestamp_str)

    # 2. Get latest calibrated weights for this category
    hybrid_w, gate_g, hedge_h, source_desc = load_latest_weights(category)

    # 3. Compute weighted contributions and final prediction
    contributions = {exp: hybrid_w[exp] * raw_preds[exp] for exp in CATEGORIES}
    final_prediction = sum(contributions.values())

    return {
        "final_prediction": final_prediction,
        "raw_preds": raw_preds,
        "hybrid_w": hybrid_w,
        "gate_g": gate_g,
        "hedge_h": hedge_h,
        "contributions": contributions,
        "source_desc": source_desc,
    }


def print_report(category: str, timestamp_str: str, result: dict):
    """Prints a formatted MoE prediction report."""
    print()
    print("=" * 76)
    print("        FEDRA MAIN PREDICTION REPORT (READ-ONLY INFERENCE)")
    print("=" * 76)
    print(f" Target Timestamp : {timestamp_str}")
    print(f" Target Category  : {category.upper()}")
    print(f" Weight Source    : {result['source_desc']}")
    print("-" * 76)
    print(f" {'EXPERT':<12} | {'RAW PRED':<12} | {'GATE (g_i)':<11} | {'HEDGE (h_i)':<12} | {'WEIGHT (w_i)':<12} | {'CONTRIB'}")
    print("-" * 76)
    for exp in CATEGORIES:
        raw = f"{result['raw_preds'][exp]:.2f} kWh"
        g = f"{result['gate_g'][exp]*100:.1f} %"
        h = f"{result['hedge_h'][exp]*100:.1f} %"
        w = f"{result['hybrid_w'][exp]*100:.1f} %"
        c = f"{result['contributions'][exp]:.2f} kWh"
        print(f" {exp.capitalize():<12} | {raw:>12} | {g:>11} | {h:>12} | {w:>12} | {c:>11}")
    print("=" * 76)
    print(f" >>> FINAL PREDICTED ELECTRICITY CONSUMPTION : {result['final_prediction']:.2f} kWh")
    print("=" * 76)
    print()


# ============================================================
# Main Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="FEDRA Main Inference CLI")
    parser.add_argument(
        "--time", "-t",
        type=str,
        default=None,
        help="Date and time string (e.g., '2026-10-15 14:00:00')"
    )
    parser.add_argument(
        "--category", "-c",
        type=str,
        choices=["academic", "residential", "others"],
        default=None,
        help="Target building category"
    )

    args = parser.parse_args()

    try:
        models = load_models()
    except Exception as e:
        print(f"\n[ERROR] Failed to load models: {e}")
        return

    # If CLI arguments are provided, run directly
    if args.time and args.category:
        res = run_prediction(args.category, args.time, models)
        print_report(args.category, args.time, res)
        return

    # Otherwise, interactive prompt mode
    print("=" * 76)
    print("         FEDRA MAIN INFERENCE CLI (LATEST DYNAMIC WEIGHTS)")
    print("=" * 76)
    print(" Mode : Pure Prediction (Does NOT ask for actual value / does NOT update weights)")
    print(" Note : Uses latest learned weights from dynamic calibration.")
    print("=" * 76)

    while True:
        ts_input = input("\nEnter target timestamp [YYYY-MM-DD HH:MM:SS] (or 'q' to quit): ").strip()
        if ts_input.lower() in ["q", "exit", "quit"]:
            break
        if not ts_input:
            ts_input = "2026-10-15 14:00:00"
            print(f"  (Using default timestamp: {ts_input})")

        cat_input = input("Enter building category [academic / residential / others]: ").strip().lower()
        if cat_input.lower() in ["q", "exit", "quit"]:
            break
        if cat_input not in CATEGORIES:
            print(f"  [!] Invalid category '{cat_input}'. Please choose from {CATEGORIES}.")
            continue

        try:
            res = run_prediction(cat_input, ts_input, models)
            print_report(cat_input, ts_input, res)
        except Exception as e:
            print(f"  [!] Inference failed: {e}")


if __name__ == "__main__":
    main()
