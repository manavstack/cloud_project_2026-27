import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from core.alerts import send_alert  # noqa: E402


def lambda_handler(event, context):
    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body)
    elif body is None:
        body = {}

    building_id = body.get("building_id", "unknown")
    forecast_kw = float(body.get("forecast_kw", 0))
    message = send_alert(building_id, forecast_kw)

    return {"statusCode": 200, "body": json.dumps({"status": "alert_sent", "message": message})}

