"""
schedule/handler.py — GET + POST /schedule
Federated Campus Energy Cloud

GET  /schedule  — Returns current recommended HVAC/EV/battery schedule from DynamoDB.
POST /schedule  — Writes an approved schedule to DynamoDB and publishes an MQTT
                  action message to AWS IoT Core topic  campus/bms/action  so the
                  building-management system (BMS) can execute it.

DynamoDB table: Schedules
  PK: scheduleId  (string, "active" = current approved schedule)
  Attributes:
    actions      (list of objects: {name, description, time, status})
    approvedAt   (string, ISO-8601)
    approvedBy   (string, Cognito username)
    roundNumber  (number)
"""

import json
import os
import boto3
from decimal import Decimal
from datetime import datetime, timezone

REGION         = os.environ.get('AWS_REGION', 'ap-south-1')
TABLE_NAME     = os.environ.get('SCHEDULES_TABLE', 'CampusEnergy-Schedules')
IOT_ENDPOINT   = os.environ.get('IOT_ENDPOINT', '')   # e.g. abcdef-ats.iot.ap-south-1.amazonaws.com
IOT_TOPIC      = os.environ.get('IOT_TOPIC', 'campus/bms/action')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table    = dynamodb.Table(TABLE_NAME)

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Content-Type': 'application/json',
}


def _decimal_to_float(obj):
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def _publish_to_iot(payload: dict):
    """Publish approved schedule action to IoT Core MQTT topic."""
    if not IOT_ENDPOINT:
        print('[schedule] IOT_ENDPOINT not set — skipping MQTT publish.')
        return
    try:
        iot = boto3.client('iot-data', endpoint_url=f'https://{IOT_ENDPOINT}', region_name=REGION)
        iot.publish(
            topic=IOT_TOPIC,
            qos=1,
            payload=json.dumps(payload).encode('utf-8'),
        )
        print(f'[schedule] Published to {IOT_TOPIC}: {payload}')
    except Exception as exc:
        print(f'[schedule] IoT publish failed: {exc}')


def handler(event, context):
    method = event.get('httpMethod', 'GET')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    # ── GET /schedule ──────────────────────────────────────────────────────
    if method == 'GET':
        try:
            resp = table.get_item(Key={'scheduleId': 'active'})
            item = resp.get('Item')
            if not item:
                return {
                    'statusCode': 404,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'error': 'No active schedule found.'}),
                }
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps(_decimal_to_float(item)),
            }
        except Exception as exc:
            return {'statusCode': 500, 'headers': CORS_HEADERS, 'body': json.dumps({'error': str(exc)})}

    # ── POST /schedule ─────────────────────────────────────────────────────
    if method == 'POST':
        try:
            body = json.loads(event.get('body') or '{}')
            # Extract Cognito username from JWT claims
            claims = (event.get('requestContext') or {}).get('authorizer', {}).get('claims', {})
            username = claims.get('cognito:username', 'unknown')

            record = {
                'scheduleId': 'active',
                'actions':    body.get('actions', []),
                'roundNumber': body.get('round', 0),
                'approvedBy': username,
                'approvedAt': datetime.now(timezone.utc).isoformat(),
                'status':     'approved',
            }
            table.put_item(Item=record)

            # Notify BMS via IoT Core
            _publish_to_iot({
                'event':    'schedule_approved',
                'actions':  body.get('actions', []),
                'approvedBy': username,
                'timestamp': record['approvedAt'],
            })

            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': 'Schedule approved and published to BMS.', 'approvedAt': record['approvedAt']}),
            }
        except Exception as exc:
            return {'statusCode': 500, 'headers': CORS_HEADERS, 'body': json.dumps({'error': str(exc)})}

    return {'statusCode': 405, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Method not allowed'})}
