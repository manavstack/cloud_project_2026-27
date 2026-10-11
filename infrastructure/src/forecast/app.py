"""Short-term demand forecaster.

Default: a simple persistence baseline (mean of the latest readings), so the
control loop works end to end. If SAGEMAKER_ENDPOINT is set, the endpoint is
called instead and the baseline is used only as a fallback.

SageMaker request : {"building_id": "...", "recent_kw": [..], "horizon_min": 15, "ts": "..."}
SageMaker response: {"predicted_kw": 12.3}
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
readings = dynamodb.Table(os.environ["READINGS_TABLE"])
buildings = dynamodb.Table(os.environ["BUILDINGS_TABLE"])
forecasts = dynamodb.Table(os.environ["FORECASTS_TABLE"])

ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT", "")
HORIZONS_MIN = (15, 30)
MAX_STALENESS = timedelta(hours=1)
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

_runtime = None


def _sagemaker():
    global _runtime
    if _runtime is None:
        _runtime = boto3.client("sagemaker-runtime")
    return _runtime


def _scan_all(table):
    items, kwargs = [], {}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def _predict(building_id, recent_kw, horizon_min, now):
    baseline = sum(recent_kw) / len(recent_kw)
    if not ENDPOINT:
        return baseline, "baseline-persistence-v1"
    try:
        resp = _sagemaker().invoke_endpoint(
            EndpointName=ENDPOINT,
            ContentType="application/json",
            Body=json.dumps(
                {
                    "building_id": building_id,
                    "recent_kw": recent_kw,
                    "horizon_min": horizon_min,
                    "ts": now.strftime(TS_FMT),
                }
            ),
        )
        predicted = float(json.loads(resp["Body"].read())["predicted_kw"])
        return predicted, "sagemaker:{}".format(ENDPOINT)
    except Exception:  # fall back so the control loop keeps working
        logger.exception("SageMaker call failed for %s; using baseline", building_id)
        return baseline, "baseline-persistence-v1"


def lambda_handler(event, context):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    written = 0

    for b in _scan_all(buildings):
        building_id = b["building_id"]
        resp = readings.query(
            KeyConditionExpression=Key("building_id").eq(building_id),
            ScanIndexForward=False,
            Limit=8,
        )
        items = [i for i in resp.get("Items", []) if "power_kw" in i]
        if not items:
            continue
        latest = datetime.strptime(items[0]["ts"], TS_FMT).replace(tzinfo=timezone.utc)
        if now - latest > MAX_STALENESS:
            logger.info("Skipping %s: latest reading is stale (%s)", building_id, items[0]["ts"])
            continue
        recent_kw = [float(i["power_kw"]) for i in items[:4]]

        for horizon in HORIZONS_MIN:
            predicted, version = _predict(building_id, recent_kw, horizon, now)
            forecasts.put_item(
                Item={
                    "building_id": building_id,
                    "target_ts": (now + timedelta(minutes=horizon)).strftime(TS_FMT),
                    "horizon_min": horizon,
                    "predicted_kw": Decimal(str(round(predicted, 4))),
                    "model_version": version,
                    "created_at": now.strftime(TS_FMT),
                }
            )
            written += 1

    logger.info("Wrote %d forecasts", written)
    return {"forecasts": written}
