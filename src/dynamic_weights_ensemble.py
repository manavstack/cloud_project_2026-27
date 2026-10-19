"""
dynamic_weights_ensemble.py
===========================
Hybrid Adaptive Mixture-of-Experts (MoE) with 3x3 Category-Conditioned Weight Matrix:

    W = [
        [ w_AA, w_AR, w_AO ],   # Academic Target Row (sum = 1.0)
        [ w_RA, w_RR, w_RO ],   # Residential Target Row (sum = 1.0)
        [ w_OA, w_OR, w_OO ]    # Others Target Row (sum = 1.0)
    ]

Each row answers: "When predicting this category, which expert has been most reliable?"
Updating one category (e.g., Residential) ONLY adapts row R, leaving rows A and O independent.

Telemetry:
  - Full per-step logs written to PostgreSQL table `moe_prediction_history`.
  - State persisted to `models/hybrid_moe_state.json`.

runcommand: docker run -it --rm --env-file .env --add-host=host.docker.internal:host-gateway -v 
"${PWD}/models:/app/models" -v "${PWD}/src:/app/src" cloud_project_2026-27-ml python src/dynamic_weights_ensemble.py   

"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import psycopg2

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from features import create_features
from db import DB_CONFIG


# ============================================================
# Configuration
# ============================================================

if os.path.exists("/app/models"):
    MODEL_DIR = "/app/models"
else:
    MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_models", "hybrid_moe_state.json")

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
# Database Telemetry & History Logger
# ============================================================

def init_history_table():
    """Ensures the moe_prediction_history table exists in PostgreSQL."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS moe_prediction_history (
        id BIGSERIAL PRIMARY KEY,

        target_category VARCHAR(20) NOT NULL,
        target_timestamp TIMESTAMP NOT NULL,

        actual_consumption NUMERIC,

        academic_prediction NUMERIC NOT NULL,
        residential_prediction NUMERIC NOT NULL,
        others_prediction NUMERIC NOT NULL,

        academic_error NUMERIC,
        residential_error NUMERIC,
        others_error NUMERIC,

        gate_academic NUMERIC NOT NULL,
        gate_residential NUMERIC NOT NULL,
        gate_others NUMERIC NOT NULL,

        hedge_academic NUMERIC NOT NULL,
        hedge_residential NUMERIC NOT NULL,
        hedge_others NUMERIC NOT NULL,

        final_academic NUMERIC NOT NULL,
        final_residential NUMERIC NOT NULL,
        final_others NUMERIC NOT NULL,

        ensemble_prediction NUMERIC NOT NULL,
        ensemble_error NUMERIC,

        new_academic_weight NUMERIC,
        new_residential_weight NUMERIC,
        new_others_weight NUMERIC,
        new_weights_ratio VARCHAR(60),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ALTER TABLE moe_prediction_history ADD COLUMN IF NOT EXISTS new_academic_weight NUMERIC;
    ALTER TABLE moe_prediction_history ADD COLUMN IF NOT EXISTS new_residential_weight NUMERIC;
    ALTER TABLE moe_prediction_history ADD COLUMN IF NOT EXISTS new_others_weight NUMERIC;
    ALTER TABLE moe_prediction_history ADD COLUMN IF NOT EXISTS new_weights_ratio VARCHAR(60);
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute(create_sql)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [DB WARNING] Could not verify table 'moe_prediction_history': {e}")


def log_prediction_to_db(record: dict) -> int:
    """Inserts a complete prediction event into moe_prediction_history."""
    insert_sql = """
    INSERT INTO moe_prediction_history (
        target_category,
        target_timestamp,
        actual_consumption,
        academic_prediction,
        residential_prediction,
        others_prediction,
        academic_error,
        residential_error,
        others_error,
        gate_academic,
        gate_residential,
        gate_others,
        hedge_academic,
        hedge_residential,
        hedge_others,
        final_academic,
        final_residential,
        final_others,
        ensemble_prediction,
        ensemble_error,
        new_academic_weight,
        new_residential_weight,
        new_others_weight,
        new_weights_ratio
    ) VALUES (
        %(target_category)s,
        %(target_timestamp)s,
        %(actual_consumption)s,
        %(academic_prediction)s,
        %(residential_prediction)s,
        %(others_prediction)s,
        %(academic_error)s,
        %(residential_error)s,
        %(others_error)s,
        %(gate_academic)s,
        %(gate_residential)s,
        %(gate_others)s,
        %(hedge_academic)s,
        %(hedge_residential)s,
        %(hedge_others)s,
        %(final_academic)s,
        %(final_residential)s,
        %(final_others)s,
        %(ensemble_prediction)s,
        %(ensemble_error)s,
        %(new_academic_weight)s,
        %(new_residential_weight)s,
        %(new_others_weight)s,
        %(new_weights_ratio)s
    ) RETURNING id;
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute(insert_sql, record)
            record_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return record_id
    except Exception as e:
        print(f"  [DB ERROR] Failed to log history to PostgreSQL: {e}")
        return -1


# ============================================================
# Hybrid Adaptive MoE Combiner (3x3 Weight Matrix)
# ============================================================

class HybridAdaptiveMoE:
    """
    Maintains 3 independent adaptive weight vectors (a 3x3 matrix):
        Row 0: Academic Target    -> [w_AA, w_AR, w_AO]
        Row 1: Residential Target -> [w_RA, w_RR, w_RO]
        Row 2: Others Target      -> [w_OA, w_OR, w_OO]
    """

    def __init__(
        self,
        gate_lr: float = 0.05,
        hedge_eta: float = 0.5,
        hedge_alpha: float = 0.03,
    ):
        self.gate_lr = gate_lr
        self.hedge_eta = hedge_eta
        self.hedge_alpha = hedge_alpha
        self.num_experts = len(CATEGORIES)

        # 3 Independent category states
        self.state = {
            cat: {
                "z": {exp: 0.0 for exp in CATEGORIES},
                "h": {exp: 1.0 / self.num_experts for exp in CATEGORIES},
            }
            for cat in CATEGORIES
        }
        self.load_state()

    def load_state(self):
        """Loads state from disk if available."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    saved = json.load(f)
                for cat in CATEGORIES:
                    if cat in saved:
                        self.state[cat]["z"] = saved[cat].get("z", self.state[cat]["z"])
                        self.state[cat]["h"] = saved[cat].get("h", self.state[cat]["h"])
            except Exception:
                pass

    def save_state(self):
        """Saves current 3x3 gating and hedge parameters."""
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def softmax(logits_dict: dict) -> dict:
        """Numerically stable softmax."""
        keys = list(logits_dict.keys())
        values = np.array([logits_dict[k] for k in keys], dtype=float)
        shifted = values - np.max(values)
        exp_vals = np.exp(shifted)
        probs = exp_vals / np.sum(exp_vals)
        return {k: float(p) for k, p in zip(keys, probs)}

    def get_category_weights(self, category: str) -> tuple:
        """
        Returns (hybrid_w, gate_g, hedge_h) for a specific target category.
        """
        cat_state = self.state[category]
        gate_g = self.softmax(cat_state["z"])
        hedge_h = cat_state["h"].copy()

        unnorm_w = {exp: gate_g[exp] * hedge_h[exp] for exp in CATEGORIES}
        sum_w = sum(unnorm_w.values())
        if sum_w <= 0:
            hybrid_w = {exp: 1.0 / self.num_experts for exp in CATEGORIES}
        else:
            hybrid_w = {exp: unnorm_w[exp] / sum_w for exp in CATEGORIES}

        return hybrid_w, gate_g, hedge_h

    def get_full_3x3_matrix(self) -> dict:
        """
        Computes the complete 3x3 adaptive weight matrix W:
            W[target_cat][expert] = final influence weight
        """
        matrix = {}
        for cat in CATEGORIES:
            hybrid_w, _, _ = self.get_category_weights(cat)
            matrix[cat] = hybrid_w
        return matrix

    def forward(self, category: str, expert_preds: dict) -> dict:
        """
        Evaluates prediction using target category's independent row of weights:
            y_hat = w_{cA} * y_A + w_{cR} * y_R + w_{cO} * y_O
        """
        hybrid_w, gate_g, hedge_h = self.get_category_weights(category)

        contributions = {exp: hybrid_w[exp] * expert_preds[exp] for exp in CATEGORIES}
        final_prediction = sum(contributions.values())

        return {
            "final_prediction": final_prediction,
            "hybrid_w": hybrid_w,
            "gate_g": gate_g,
            "hedge_h": hedge_h,
            "contributions": contributions,
        }

    def step(self, category: str, expert_preds: dict, actual_y: float, forward_out: dict) -> dict:
        """
        Updates strictly the row corresponding to `category`.
        Other 2 categories remain completely unchanged.
        """
        y_hat = forward_out["final_prediction"]
        hybrid_w = forward_out["hybrid_w"]
        gate_g = forward_out["gate_g"]
        old_h = forward_out["hedge_h"]
        old_z = self.state[category]["z"].copy()

        # 1. HEDGE / EWA UPDATE on target category row
        errors = {exp: abs(actual_y - expert_preds[exp]) for exp in CATEGORIES}
        max_err = max(errors.values())
        norm_losses = {exp: (errors[exp] / max_err) if max_err > 0 else 0.0 for exp in CATEGORIES}

        updated_h_unnorm = {
            exp: old_h[exp] * np.exp(-self.hedge_eta * norm_losses[exp])
            for exp in CATEGORIES
        }
        total_h = sum(updated_h_unnorm.values())
        norm_h = {exp: updated_h_unnorm[exp] / total_h for exp in CATEGORIES}

        uniform_prior = 1.0 / self.num_experts
        new_h = {
            exp: (1.0 - self.hedge_alpha) * norm_h[exp] + self.hedge_alpha * uniform_prior
            for exp in CATEGORIES
        }
        sum_new_h = sum(new_h.values())
        new_h = {exp: new_h[exp] / sum_new_h for exp in CATEGORIES}

        # 2. BACKPROPAGATION UPDATE on target category gate
        prediction_error = y_hat - actual_y
        scale = max(abs(prediction_error), 100.0)
        norm_error = prediction_error / scale

        new_z = {}
        for k in CATEGORIES:
            grad_k = norm_error * hybrid_w[k] * ((expert_preds[k] - y_hat) / scale)
            new_z[k] = old_z[k] - self.gate_lr * grad_k

        mean_z = np.mean(list(new_z.values()))
        new_z = {exp: z - mean_z for exp, z in new_z.items()}

        # 3. COMMIT UPDATES TO THIS ROW ONLY
        self.state[category]["z"] = new_z
        self.state[category]["h"] = new_h
        self.save_state()

        new_hybrid_w, new_gate_g, _ = self.get_category_weights(category)

        return {
            "errors": errors,
            "old_h": old_h,
            "new_h": new_h,
            "old_gate_g": gate_g,
            "new_gate_g": new_gate_g,
            "old_hybrid_w": hybrid_w,
            "new_hybrid_w": new_hybrid_w,
        }


# ============================================================
# Helpers
# ============================================================

def print_3x3_matrix(matrix: dict, highlight_category: str = None):
    """Prints the 3x3 Category-Conditioned Weight Matrix."""
    print("  " + "┌" + "─" * 68 + "┐")
    print("  │            3x3 CATEGORY-CONDITIONED WEIGHT MATRIX W              │")
    print("  │            (Each row is independent and sums to 100%)            │")
    print("  ├──────────────┬──────────────────┬──────────────────┬─────────────┤")
    print("  │ TARGET CAT   │ ACADEMIC EXPERT  │ RESIDENTIAL EXP  │ OTHERS EXP  │")
    print("  ├──────────────┼──────────────────┼──────────────────┼─────────────┤")
    for cat in CATEGORIES:
        row = matrix[cat]
        marker = "▶ " if cat == highlight_category else "  "
        print(f"  │ {marker}{cat.capitalize():<11} │ {row['academic']*100:>14.1f} % │ {row['residential']*100:>14.1f} % │ {row['others']*100:>9.1f} % │")
    print("  └──────────────┴──────────────────┴──────────────────┴─────────────┘")


def load_all_models() -> dict:
    models = {}
    for cat in CATEGORIES:
        path = os.path.join(MODEL_DIR, f"{cat}_expert.pkl")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing model binary '{path}'. Run train_experts.py first.")
        models[cat] = joblib.load(path)
    return models


def predict_raw_experts(models: dict, timestamp_str: str) -> dict:
    df = pd.DataFrame([{"reading_time": timestamp_str}])
    df = create_features(df)
    X = df[FEATURE_COLS]
    return {cat: float(models[cat].predict(X)[0]) for cat in CATEGORIES}


# ============================================================
# Interactive Session
# ============================================================

def run_interactive_session():
    print("=" * 76)
    print("  FEDRA 3x3 CATEGORY-CONDITIONED HYBRID ADAPTIVE MoE")
    print("=" * 76)
    print("  Architecture: 3 Independent Weight Sets (3x3 Matrix W)")
    print("  - Academic target row    : [w_AA, w_AR, w_AO]")
    print("  - Residential target row : [w_RA, w_RR, w_RO]")
    print("  - Others target row      : [w_OA, w_OR, w_OO]")
    print("  Commands: Type 'exit' or 'q' at any prompt to quit.")
    print("=" * 76)

    init_history_table()

    try:
        models = load_all_models()
    except Exception as e:
        print(f"\n[ERROR] Could not load models: {e}")
        return

    moe = HybridAdaptiveMoE(gate_lr=0.5, hedge_eta=0.6, hedge_alpha=0.03)
    step = 1

    # Show initial 3x3 matrix on startup
    print("\n[ACTIVE 3x3 WEIGHT MATRIX]")
    print_3x3_matrix(moe.get_full_3x3_matrix())

    while True:
        print(f"\n{'='*32} [ STEP #{step} ] {'='*32}")

        # 1. Target Timestamp
        ts_input = input("Enter target timestamp [YYYY-MM-DD HH:MM:SS] (e.g. 2026-10-15 14:00:00): ").strip()
        if ts_input.lower() in ["exit", "q", "quit"]:
            break
        if not ts_input:
            ts_input = "2026-10-15 14:00:00"
            print(f"  (Using default timestamp: {ts_input})")

        # 2. Building Category
        cat_input = input("Enter building category [academic / residential / others]: ").strip().lower()
        if cat_input.lower() in ["exit", "q", "quit"]:
            break
        if cat_input not in CATEGORIES:
            print(f"  [!] Invalid category '{cat_input}'. Please choose from {CATEGORIES}.")
            continue

        # 3. Generate Expert Predictions
        try:
            raw_preds = predict_raw_experts(models, ts_input)
        except Exception as e:
            print(f"  [!] Prediction error: {e}")
            continue

        # 4. Forward Pass using category's dedicated row of weights
        forward_out = moe.forward(cat_input, raw_preds)
        final_kwh = forward_out["final_prediction"]
        hybrid_w = forward_out["hybrid_w"]
        gate_g = forward_out["gate_g"]
        hedge_h = forward_out["hedge_h"]
        contribs = forward_out["contributions"]

        # 5. Display Prediction Report for this Category
        print("\n" + "-" * 76)
        print(f"  PREDICTION REPORT  |  Target Category: {cat_input.upper()}  |  Time: {ts_input}")
        print("-" * 76)
        print(f"  {'EXPERT':<12} | {'RAW PRED':<12} | {'GATE (g_i)':<11} | {'HEDGE (h_i)':<12} | {'WEIGHT (w_i)':<12} | {'CONTRIB'}")
        print("-" * 76)
        for exp in CATEGORIES:
            raw_val = f"{raw_preds[exp]:.2f} kWh"
            g_pct = f"{gate_g[exp]*100:.1f} %"
            h_pct = f"{hedge_h[exp]*100:.1f} %"
            w_pct = f"{hybrid_w[exp]*100:.1f} %"
            c_val = f"{contribs[exp]:.2f} kWh"
            print(f"  {exp.capitalize():<12} | {raw_val:>12} | {g_pct:>11} | {h_pct:>12} | {w_pct:>12} | {c_val:>11}")
        print("-" * 76)
        print(f"  >>> COMBINED PREDICTION FOR {cat_input.upper()} : {final_kwh:.2f} kWh")
        print("=" * 76)

        # 6. Ask for Actual Ground Truth
        actual_input = input("\nEnter actual observed consumption (kWh) [or Press Enter to skip update]: ").strip()
        if actual_input.lower() in ["exit", "q", "quit"]:
            break

        actual_val = None
        err_moe = None
        expert_errors = {exp: None for exp in CATEGORIES}

        if actual_input:
            try:
                actual_val = float(actual_input)
                # 7. Backward Step: Update strictly this category's row
                upd = moe.step(cat_input, raw_preds, actual_val, forward_out)
                expert_errors = upd["errors"]
                err_moe = abs(actual_val - final_kwh)

                print("\n" + "-" * 76)
                print(f"  ROW UPDATE FOR '{cat_input.upper()}' (Observed: {actual_val:.2f} kWh | Error: {err_moe:.2f} kWh)")
                print("-" * 76)
                for exp in CATEGORIES:
                    e_str = f"{expert_errors[exp]:.1f} kWh"
                    w_trans = f"{upd['old_hybrid_w'][exp]*100:.1f}% -> {upd['new_hybrid_w'][exp]*100:.1f}%"
                    print(f"  {exp.capitalize():<12} Expert | Error: {e_str:>10} | Weight: {w_trans}")
                print("-" * 76)
                print(f"  ✓ Only row '{cat_input.upper()}' updated. Other rows remained unchanged.")

                # Display updated 3x3 matrix
                print(f"\n[UPDATED 3x3 WEIGHT MATRIX (Row ▶ {cat_input.upper()} adapted)]")
                print_3x3_matrix(moe.get_full_3x3_matrix(), highlight_category=cat_input)

            except ValueError:
                print("  [!] Invalid number entered. State unchanged.")
                actual_val = None
        else:
            print("  (Update skipped. Current weights preserved.)")

        new_w = upd["new_hybrid_w"] if (actual_val is not None and "upd" in locals()) else hybrid_w
        ratio_str = f"A:{new_w['academic']*100:.1f}% | R:{new_w['residential']*100:.1f}% | O:{new_w['others']*100:.1f}%"

        # 8. Log Telemetry to PostgreSQL
        history_record = {
            "target_category": cat_input,
            "target_timestamp": ts_input,
            "actual_consumption": actual_val,
            "academic_prediction": raw_preds["academic"],
            "residential_prediction": raw_preds["residential"],
            "others_prediction": raw_preds["others"],
            "academic_error": expert_errors["academic"],
            "residential_error": expert_errors["residential"],
            "others_error": expert_errors["others"],
            "gate_academic": gate_g["academic"],
            "gate_residential": gate_g["residential"],
            "gate_others": gate_g["others"],
            "hedge_academic": hedge_h["academic"],
            "hedge_residential": hedge_h["residential"],
            "hedge_others": hedge_h["others"],
            "final_academic": hybrid_w["academic"],
            "final_residential": hybrid_w["residential"],
            "final_others": hybrid_w["others"],
            "ensemble_prediction": final_kwh,
            "ensemble_error": err_moe,
            "new_academic_weight": float(new_w["academic"]),
            "new_residential_weight": float(new_w["residential"]),
            "new_others_weight": float(new_w["others"]),
            "new_weights_ratio": ratio_str,
        }

        row_id = log_prediction_to_db(history_record)
        if row_id > 0:
            print(f"  ✓ Telemetry recorded in PostgreSQL table 'moe_prediction_history' (Row ID: {row_id}).")

        step += 1

    print("\nSession ended. Telemetry successfully stored in PostgreSQL.")


if __name__ == "__main__":
    run_interactive_session()
