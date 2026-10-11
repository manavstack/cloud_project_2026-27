"""IoT telemetry -> validate -> S3 (raw archive) + DynamoDB (structured) + SNS (alerts).

The IoT rule adds `building_id` (from topic campus/<building_id>/telemetry) and
`ingest_ts` (ms epoch). Device payload (JSON):
    {"ts": "2026-10-11T10:15:00Z", "power_kw": 12.4, "voltage_v": 231.0,
     "temperature_c": 26.1, "humidity_pct": 55, "occupancy_count": 34}
"""
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")

RAW_BUCKET = os.environ["RAW_BUCKET"]
ALERT_TOPIC = os.environ["ALERT_TOPIC"]
PEAK_KW = float(os.environ.get("PEAK_KW", "50"))
MAX_VALID_KW = float(os.environ.get("MAX_VALID_KW", "5000"))

readings = dynamodb.Table(os.environ["READINGS_TABLE"])
buildings = dynamodb.Table(os.environ["BUILDINGS_TABLE"])
alerts = dynamodb.Table(os.environ["ALERTS_TABLE"])

BUILDING_RE = re.compile(r"^[a-z0-9_\-]{1,64}$")
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _parse_ts(event):
    value = event.get("ts")
    if value is None:
        value = event.get("ingest_ts")
        if value is None:
            return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _num(event, key):
    value = event.get(key)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dec(value):
    return None if value is None else Decimal(str(round(value, 4)))


def _put_if_absent(table, item, key_name):
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists({})".format(key_name))
        return True
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def lambda_handler(event, context):
    building_id = str(event.get("building_id", ""))
    if not BUILDING_RE.match(building_id):
        logger.warning("Dropping message with invalid building_id: %r", building_id)
        return {"status": "dropped", "reason": "invalid building_id"}

    try:
        ts = _parse_ts(event)
    except ValueError:
        logger.warning("Dropping message with unparseable timestamp for %s", building_id)
        return {"status": "dropped", "reason": "invalid timestamp"}

    power_kw = _num(event, "power_kw")
    voltage_v = _num(event, "voltage_v")
    temperature_c = _num(event, "temperature_c")
    humidity_pct = _num(event, "humidity_pct")
    occupancy = event.get("occupancy_count")
    if isinstance(occupancy, bool) or not isinstance(occupancy, (int, float)) or occupancy < 0:
        occupancy = None
    else:
        occupancy = int(occupancy)

    # Cleaning: flag suspicious values instead of silently discarding them
    flag = "ok"
    if power_kw is None:
        flag = "missing_power"
    elif power_kw < 0 or power_kw > MAX_VALID_KW:
        flag = "outlier"
        power_kw = None
    if humidity_pct is not None and not 0 <= humidity_pct <= 100:
        humidity_pct = None
        if flag == "ok":
            flag = "outlier"

    ts_str = ts.strftime(TS_FMT)

    # 1) Raw archive (partitioned for Athena / SageMaker use)
    key = "readings/building_id={}/date={}/{}-{}.json".format(
        building_id, ts.strftime("%Y-%m-%d"), ts.strftime("%H%M%S"), uuid.uuid4().hex[:8]
    )
    record = {
        "building_id": building_id,
        "ts": ts_str,
        "power_kw": power_kw,
        "voltage_v": voltage_v,
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "occupancy_count": occupancy,
        "quality_flag": flag,
    }
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(record).encode("utf-8"),
        ContentType="application/json",
    )

    # 2) Structured store (idempotent: IoT may redeliver)
    _put_if_absent(buildings, {"building_id": building_id, "building_type": "unknown"}, "building_id")
    item = {
        "building_id": building_id,
        "ts": ts_str,
        "power_kw": _dec(power_kw),
        "voltage_v": _dec(voltage_v),
        "temperature_c": _dec(temperature_c),
        "humidity_pct": _dec(humidity_pct),
        "occupancy_count": occupancy,
        "quality_flag": flag,
    }
    item = {k: v for k, v in item.items() if v is not None}
    _put_if_absent(readings, item, "building_id")

    # 3) Real-time alerting
    alert_type = None
    if flag == "outlier":
        alert_type = "anomaly"
    elif power_kw is not None and power_kw >= PEAK_KW:
        alert_type = "peak_demand"

    if alert_type:
        alert = {
            "building_id": building_id,
            "created_at": "{}#{}".format(ts_str, alert_type),
            "alert_type": alert_type,
            "threshold": _dec(PEAK_KW),
        }
        if power_kw is not None:
            alert["value"] = _dec(power_kw)
        alerts.put_item(Item=alert)
        sns.publish(
            TopicArn=ALERT_TOPIC,
            Subject="Campus energy alert: {} ({})".format(alert_type, building_id)[:100],
            Message=json.dumps(record, indent=2),
        )

    return {"status": "ok", "flag": flag, "alert": alert_type}
