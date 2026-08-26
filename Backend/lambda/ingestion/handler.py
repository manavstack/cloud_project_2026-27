import json
import uuid
import sys
from pathlib import Path

# Allow `from core.storage import ...` whether this file is run standalone
# (local dev) or packaged/deployed on its own (AWS Lambda zip).
sys.path.append(str(Path(__file__).resolve().parents[2]))
from core.storage import save_reading  # noqa: E402


def lambda_handler(event, context):
    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body)
    elif body is None:
        body = {}

    required = {"building_id", "timestamp", "power_kw", "temperature", "occupancy"}
    missing = required - body.keys()
    if missing:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"missing fields: {sorted(missing)}"}),
        }

    body["reading_id"] = str(uuid.uuid4())
    save_reading(body)

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "stored", "reading_id": body["reading_id"]}),
    }

