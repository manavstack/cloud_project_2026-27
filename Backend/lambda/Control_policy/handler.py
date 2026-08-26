import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).resolve().parents[2]))
from core.storage import get_all_readings  # noqa: E402
from core.alerts import send_alert  # noqa: E402

# Example peak-tariff window: 6 PM - 10 PM. Adjust to your utility's actual tariff table.
PEAK_TARIFF_HOURS = set(range(18, 22))
DEMAND_THRESHOLD_KW = 60.0


def get_latest_reading_per_building():
    """
    Stand-in for calling the SageMaker forecast endpoint: uses the most recent
    ingested reading per building as the "forecast" signal. Swap this out for
    a real SageMaker endpoint call once the model is deployed (see
    sagemaker/train_forecast_model.py).
    """
    readings = get_all_readings()
    latest = {}
    for r in readings:
        b = r["building_id"]
        if b not in latest or str(r["timestamp"]) > str(latest[b]["timestamp"]):
            latest[b] = r
    return latest


def decide_action(forecast_kw: float, hour: int):
    if hour in PEAK_TARIFF_HOURS and forecast_kw > DEMAND_THRESHOLD_KW:
        return ["reduce_hvac_setpoint", "dim_non_critical_lighting"]
    if forecast_kw > DEMAND_THRESHOLD_KW:
        return ["pre_cool_building"]
    return ["no_action"]


def lambda_handler(event, context):
    hour = datetime.now(timezone.utc).hour
    latest = get_latest_reading_per_building()

    results = {}
    for building_id, reading in latest.items():
        forecast_kw = reading["power_kw"]
        actions = decide_action(forecast_kw, hour)
        results[building_id] = {"forecast_kw": forecast_kw, "actions": actions}

        if forecast_kw > DEMAND_THRESHOLD_KW:
            send_alert(building_id, forecast_kw)

    print(json.dumps(results, indent=2))
    return {"statusCode": 200, "body": json.dumps(results)}


if __name__ == "__main__":
    # Lets you run the control policy manually: python lambda/control_policy/handler.py
    lambda_handler({}, None)

