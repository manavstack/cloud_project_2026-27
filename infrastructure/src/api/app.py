"""Dashboard API (API Gateway HTTP API + Cognito JWT authorizer).

GET /buildings
GET /readings   ?building_id= (required) &from= &to= &limit=
GET /forecasts  ?building_id= (required) &from= &to= &limit=
GET /actions    ?building_id= &from= &to= &limit=
GET /alerts     ?building_id= &from= &to= &limit=
from/to are ISO-8601. limit defaults to 100 (max 500).
Access requires the Cognito group `admin` or `facility_staff`.
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
TABLES = {
    "readings": dynamodb.Table(os.environ["READINGS_TABLE"]),
    "forecasts": dynamodb.Table(os.environ["FORECASTS_TABLE"]),
    "actions": dynamodb.Table(os.environ["ACTIONS_TABLE"]),
    "alerts": dynamodb.Table(os.environ["ALERTS_TABLE"]),
    "buildings": dynamodb.Table(os.environ["BUILDINGS_TABLE"]),
}

ALLOWED_GROUPS = {"admin", "facility_staff"}
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

# path -> (table, sort key, building_id required)
ROUTES = {
    "/readings": ("readings", "ts", True),
    "/forecasts": ("forecasts", "target_ts", True),
    "/actions": ("actions", "created_at", False),
    "/alerts": ("alerts", "created_at", False),
}


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(type(value))


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_json_default),
    }


def _groups(event):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    raw = claims.get("cognito:groups", "")
    if isinstance(raw, list):
        return set(raw)
    return set(str(raw).strip("[]").replace(",", " ").split())


def _iso(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime(TS_FMT)


def _scan_limited(table, limit):
    items, kwargs = [], {}
    while len(items) < limit * 5:  # cap work on large tables
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return items


def lambda_handler(event, context):
    if not (_groups(event) & ALLOWED_GROUPS):
        return _response(403, {"error": "forbidden"})

    path = event.get("rawPath", "")
    query = event.get("queryStringParameters") or {}

    if path == "/buildings":
        items = _scan_limited(TABLES["buildings"], 100)
        return _response(200, {"count": len(items), "items": items})

    if path not in ROUTES:
        return _response(404, {"error": "not found"})
    table_name, sort_key, building_required = ROUTES[path]
    table = TABLES[table_name]

    try:
        limit = min(max(int(query.get("limit", 100)), 1), 500)
        start = _iso(query["from"]) if query.get("from") else None
        end = _iso(query["to"]) if query.get("to") else None
    except ValueError:
        return _response(400, {"error": "invalid query parameter"})

    building_id = query.get("building_id")
    if building_required and not building_id:
        return _response(400, {"error": "building_id is required"})

    if building_id:
        cond = Key("building_id").eq(building_id)
        # '~' sorts after '#', so suffixed keys (ts#action) on the end date are included
        if start and end:
            cond &= Key(sort_key).between(start, end + "~")
        elif start:
            cond &= Key(sort_key).gte(start)
        elif end:
            cond &= Key(sort_key).lte(end + "~")
        resp = table.query(KeyConditionExpression=cond, ScanIndexForward=False, Limit=limit)
        items = resp.get("Items", [])
    else:
        items = _scan_limited(table, limit)
        if start:
            items = [i for i in items if i[sort_key] >= start]
        if end:
            items = [i for i in items if i[sort_key] <= end + "~"]
        items.sort(key=lambda i: i[sort_key], reverse=True)
        items = items[:limit]

    return _response(200, {"count": len(items), "items": items})
