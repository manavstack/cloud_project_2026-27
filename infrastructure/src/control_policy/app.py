"""Rule-and-cost-based control policy engine (runs every 15 minutes).

If the current local hour is inside a peak-tariff window and a building's
forecast for the next ~35 minutes reaches PEAK_KW, it records RECOMMENDED actions
(HVAC set point, lighting, deferrable loads) and notifies staff through SNS.
Connect the recommendations to a building-management system to automate them.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

forecasts = dynamodb.Table(os.environ["FORECASTS_TABLE"])
buildings = dynamodb.Table(os.environ["BUILDINGS_TABLE"])
tariff = dynamodb.Table(os.environ["TARIFF_TABLE"])
actions = dynamodb.Table(os.environ["ACTIONS_TABLE"])

ALERT_TOPIC = os.environ["ALERT_TOPIC"]
PEAK_KW = float(os.environ.get("PEAK_KW", "50"))
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")
WINDOW_MIN = 35
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

# Comfort-aware limits per building type
RULES = {
    "classroom": {"hvac_setpoint_c": 1.5, "lighting_dim_pct": 20, "defer_loads": True},
    "lab": {"hvac_setpoint_c": 0.5, "lighting_dim_pct": 0, "defer_loads": False},
    "hostel": {"hvac_setpoint_c": 1.0, "lighting_dim_pct": 30, "defer_loads": True},
    "admin": {"hvac_setpoint_c": 1.5, "lighting_dim_pct": 25, "defer_loads": True},
    "library": {"hvac_setpoint_c": 1.0, "lighting_dim_pct": 10, "defer_loads": True},
}
DEFAULT_RULE = {"hvac_setpoint_c": 1.0, "lighting_dim_pct": 10, "defer_loads": False}


def _scan_all(table):
    items, kwargs = [], {}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def _peak_window(hour):
    for w in _scan_all(tariff):
        if w.get("is_peak") and int(w["start_hour"]) <= hour < int(w["end_hour"]):
            return w
    return None


def lambda_handler(event, context):
    now_local = datetime.now(ZoneInfo(TIMEZONE))
    window = _peak_window(now_local.hour)
    if window is None:
        logger.info("Not in a peak-tariff window (%s). No actions.", now_local.isoformat())
        return {"status": "off_peak", "actions": 0}

    now = datetime.now(timezone.utc).replace(microsecond=0)
    start, end = now.strftime(TS_FMT), (now + timedelta(minutes=WINDOW_MIN)).strftime(TS_FMT)
    created = 0

    for b in _scan_all(buildings):
        building_id = b["building_id"]
        resp = forecasts.query(
            KeyConditionExpression=Key("building_id").eq(building_id) & Key("target_ts").between(start, end)
        )
        values = [float(i["predicted_kw"]) for i in resp.get("Items", [])]
        if not values:
            continue
        predicted = max(values)
        if predicted < PEAK_KW:
            continue

        rule = RULES.get(b.get("building_type", ""), DEFAULT_RULE)
        reason = "Forecast {:.1f} kW >= threshold {:.1f} kW during '{}'".format(
            predicted, PEAK_KW, window.get("name", "peak tariff")
        )
        planned = []
        if rule["hvac_setpoint_c"] > 0:
            planned.append(("hvac_setpoint", "Raise cooling set point by {} C".format(rule["hvac_setpoint_c"])))
        if rule["lighting_dim_pct"] > 0:
            planned.append(("lighting_dim", "Dim non-essential lighting by {}%".format(rule["lighting_dim_pct"])))
        if rule["defer_loads"]:
            planned.append(("defer_loads", "Defer non-critical loads until the peak window ends"))

        for action_type, detail in planned:
            actions.put_item(
                Item={
                    "building_id": building_id,
                    "created_at": "{}#{}".format(start, action_type),
                    "action_type": action_type,
                    "detail": detail,
                    "reason": reason,
                    "predicted_kw": Decimal(str(round(predicted, 4))),
                    "status": "recommended",
                }
            )
            created += 1

        if planned:
            sns.publish(
                TopicArn=ALERT_TOPIC,
                Subject="Peak demand expected: {}".format(building_id)[:100],
                Message=json.dumps(
                    {
                        "building_id": building_id,
                        "predicted_kw": predicted,
                        "reason": reason,
                        "recommended_actions": [d for _, d in planned],
                    },
                    indent=2,
                ),
            )

    logger.info("Created %d recommended actions", created)
    return {"status": "peak_window", "actions": created}
