"""
auto_calibrate.py
=================
Non-interactive batch calibration of the 3×3 Hybrid Adaptive MoE
using queued ground-truth records from PostgreSQL.

Workflow:
  1. Connect to PostgreSQL → query moe_calibration_queue WHERE processed = FALSE
  2. For each row (ordered by id):
       a. Load frozen expert models → generate predictions for target_timestamp
       b. MoE forward pass using target_category's weight row
       c. MoE backward step (Hedge + Backprop) using actual_consumption
          → updates ONLY the target_category's row in the 3×3 matrix
       d. Log full telemetry to moe_prediction_history
       e. UPDATE moe_calibration_queue SET processed = TRUE, processed_at = NOW()
  3. Save final state to hybrid_moe_state.json

Run via Docker:
    
    docker run --rm --env-file .env --add-host=host.docker.internal:host-gateway -v "${PWD}/models:/app/models" -v "${PWD}/src:/app/src" cloud_project_2026-27-ml python src/auto_calibrate.py


    docker run -it --rm --env-file .env --add-host=host.docker.internal:host-gateway \
        -v "${PWD}/models:/app/models" -v "${PWD}/src:/app/src" \
        cloud_project_2026-27-ml python src/auto_calibrate.py
"""

import os
import sys
import psycopg2
from datetime import datetime

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import DB_CONFIG
from dynamic_weights_ensemble import (
    HybridAdaptiveMoE,
    load_all_models,
    predict_raw_experts,
    init_history_table,
    log_prediction_to_db,
    print_3x3_matrix,
    CATEGORIES,
)


# ============================================================
# Queue Operations
# ============================================================

def fetch_pending_rows(conn):
    """Fetch all unprocessed calibration rows ordered by id."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, target_category, target_timestamp, actual_consumption
            FROM moe_calibration_queue
            WHERE processed = FALSE
            ORDER BY id;
        """)
        rows = cur.fetchall()
    return rows


def mark_row_processed(conn, row_id: int):
    """Mark a single calibration row as processed."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE moe_calibration_queue
            SET processed = TRUE, processed_at = NOW()
            WHERE id = %s;
        """, (row_id,))
    conn.commit()


# ============================================================
# Main Calibration Loop
# ============================================================

def run_auto_calibration():
    print("=" * 76)
    print("  FEDRA AUTO-CALIBRATION — Batch Queue Processor")
    print("=" * 76)

    # 1. Ensure telemetry table exists
    init_history_table()

    # 2. Load frozen expert models
    try:
        models = load_all_models()
        print(f"  ✓ Loaded {len(models)} frozen expert models.")
    except Exception as e:
        print(f"  [FATAL] Could not load models: {e}")
        return

    # 3. Initialise MoE (loads existing 3×3 state from disk)
    moe = HybridAdaptiveMoE(gate_lr=0.5, hedge_eta=0.6, hedge_alpha=0.03)
    print("  ✓ HybridAdaptiveMoE initialised (state loaded from disk).\n")

    # Show initial 3×3 matrix
    print("[INITIAL 3×3 WEIGHT MATRIX]")
    print_3x3_matrix(moe.get_full_3x3_matrix())

    # 4. Connect to DB and fetch pending queue rows
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"  [FATAL] DB connection failed: {e}")
        return

    pending = fetch_pending_rows(conn)
    total = len(pending)

    if total == 0:
        print("\n  ✓ No unprocessed rows in moe_calibration_queue. Nothing to do.")
        conn.close()
        return

    print(f"\n  Found {total} unprocessed row(s) in moe_calibration_queue.\n")

    # Category-level counters for summary
    cat_counts = {cat: 0 for cat in CATEGORIES}
    success_count = 0
    error_count = 0

    # 5. Process each row
    for idx, (row_id, target_category, target_timestamp, actual_consumption) in enumerate(pending, 1):
        ts_str = target_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        actual_val = float(actual_consumption)

        print(f"{'='*32} [ ROW {idx}/{total} ] {'='*32}")
        print(f"  Queue ID     : {row_id}")
        print(f"  Category     : {target_category}")
        print(f"  Timestamp    : {ts_str}")
        print(f"  Actual (kWh) : {actual_val:.2f}")

        # Validate category
        if target_category not in CATEGORIES:
            print(f"  [SKIP] Unknown category '{target_category}'. Skipping.\n")
            error_count += 1
            continue

        # 5a. Generate expert predictions
        try:
            raw_preds = predict_raw_experts(models, ts_str)
        except Exception as e:
            print(f"  [ERROR] Prediction failed: {e}. Skipping.\n")
            error_count += 1
            continue

        print(f"  Expert preds : A={raw_preds['academic']:.2f}  "
              f"R={raw_preds['residential']:.2f}  "
              f"O={raw_preds['others']:.2f}")

        # 5b. Forward pass (target category's row)
        forward_out = moe.forward(target_category, raw_preds)
        ensemble_pred = forward_out["final_prediction"]
        hybrid_w = forward_out["hybrid_w"]
        gate_g = forward_out["gate_g"]
        hedge_h = forward_out["hedge_h"]

        print(f"  Ensemble pred: {ensemble_pred:.2f} kWh  "
              f"(weights: A={hybrid_w['academic']*100:.1f}%  "
              f"R={hybrid_w['residential']*100:.1f}%  "
              f"O={hybrid_w['others']*100:.1f}%)")

        # 5c. Backward step — update ONLY this category's row
        upd = moe.step(target_category, raw_preds, actual_val, forward_out)
        ensemble_error = abs(actual_val - ensemble_pred)

        print(f"  Ensemble err : {ensemble_error:.2f} kWh")
        print(f"  Weight shift : ", end="")
        shifts = []
        for exp in CATEGORIES:
            old_w = upd["old_hybrid_w"][exp] * 100
            new_w = upd["new_hybrid_w"][exp] * 100
            shifts.append(f"{exp[0].upper()}:{old_w:.1f}→{new_w:.1f}%")
        print("  ".join(shifts))

        # 5d. Log telemetry to moe_prediction_history
        expert_errors = upd["errors"]
        new_w = upd["new_hybrid_w"]
        ratio_str = f"A:{new_w['academic']*100:.1f}% | R:{new_w['residential']*100:.1f}% | O:{new_w['others']*100:.1f}%"

        history_record = {
            "target_category": target_category,
            "target_timestamp": ts_str,
            "actual_consumption": float(actual_val),
            "academic_prediction": float(raw_preds["academic"]),
            "residential_prediction": float(raw_preds["residential"]),
            "others_prediction": float(raw_preds["others"]),
            "academic_error": float(expert_errors["academic"]),
            "residential_error": float(expert_errors["residential"]),
            "others_error": float(expert_errors["others"]),
            "gate_academic": float(gate_g["academic"]),
            "gate_residential": float(gate_g["residential"]),
            "gate_others": float(gate_g["others"]),
            "hedge_academic": float(hedge_h["academic"]),
            "hedge_residential": float(hedge_h["residential"]),
            "hedge_others": float(hedge_h["others"]),
            "final_academic": float(hybrid_w["academic"]),
            "final_residential": float(hybrid_w["residential"]),
            "final_others": float(hybrid_w["others"]),
            "ensemble_prediction": float(ensemble_pred),
            "ensemble_error": float(ensemble_error),
            "new_academic_weight": float(new_w["academic"]),
            "new_residential_weight": float(new_w["residential"]),
            "new_others_weight": float(new_w["others"]),
            "new_weights_ratio": ratio_str,
        }
        hist_id = log_prediction_to_db(history_record)

        # 5e. Mark queue row as processed
        mark_row_processed(conn, row_id)
        cat_counts[target_category] += 1
        success_count += 1

        status = f"✓ Processed (history_id={hist_id})" if hist_id > 0 else "✓ Processed (telemetry log failed)"
        print(f"  {status}\n")

    conn.close()

    # 6. Final summary
    print("=" * 76)
    print("  AUTO-CALIBRATION COMPLETE")
    print("=" * 76)
    print(f"  Total rows    : {total}")
    print(f"  Succeeded     : {success_count}")
    print(f"  Errors/Skipped: {error_count}")
    print(f"  By category   : {', '.join(f'{c}={n}' for c, n in cat_counts.items() if n > 0)}")

    # Show final 3×3 matrix
    print(f"\n[FINAL 3×3 WEIGHT MATRIX]")
    print_3x3_matrix(moe.get_full_3x3_matrix())
    print(f"\n  State saved to: src/ml_models/hybrid_moe_state.json")
    print("=" * 76)


if __name__ == "__main__":
    run_auto_calibration()
