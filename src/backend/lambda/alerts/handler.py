"""
alerts/handler.py — POST /alerts  (SNS subscription webhook)
Federated Campus Energy Cloud

Amazon SNS calls this endpoint when an alert fires (peak-demand breach,
failed federated update, CloudWatch alarm).

Flow:
  CloudWatch Alarm → SNS Topic → HTTP(S) subscription → API Gateway → this Lambda
                                                                           ↓
                                                            Stores in DynamoDB Alerts table
                                                                           ↓
                                                            Broadcasts to all active WebSocket
                                                            connections via API Gateway Management API

DynamoDB tables:
  Alerts        — PK: alertId (UUID), stores alert history
  WsConnections — PK: connectionId, stores active WebSocket clients
"""

import json
import os
import uuid
import boto3
from datetime import datetime, timezone

REGION        = os.environ.get('AWS_REGION', 'ap-south-1')
ALERTS_TABLE  = os.environ.get('ALERTS_TABLE', 'CampusEnergy-Alerts')
WS_TABLE      = os.environ.get('WS_CONNECTIONS_TABLE', 'CampusEnergy-WsConnections')
WS_API_ENDPOINT = os.environ.get('WS_API_ENDPOINT', '')  # https://<id>.execute-api.<region>.amazonaws.com/<stage>

dynamodb  = boto3.resource('dynamodb', region_name=REGION)
alerts_tbl = dynamodb.Table(ALERTS_TABLE)
ws_tbl     = dynamodb.Table(WS_TABLE)

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type,x-amz-sns-message-type',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
    'Content-Type': 'application/json',
}


def _broadcast(message: dict):
    """Push alert to all active WebSocket connections."""
    if not WS_API_ENDPOINT:
        print('[alerts] WS_API_ENDPOINT not set — skipping WebSocket broadcast.')
        return

    try:
        apigw = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=WS_API_ENDPOINT,
            region_name=REGION,
        )
        payload = json.dumps({'type': 'alert', 'data': message}).encode('utf-8')

        # Scan all active connection IDs
        resp = ws_tbl.scan(ProjectionExpression='connectionId')
        for conn in resp.get('Items', []):
            cid = conn['connectionId']
            try:
                apigw.post_to_connection(ConnectionId=cid, Data=payload)
            except apigw.exceptions.GoneException:
                # Stale connection — clean up
                ws_tbl.delete_item(Key={'connectionId': cid})
                print(f'[alerts] Removed stale connection: {cid}')

    except Exception as exc:
        print(f'[alerts] Broadcast error: {exc}')


def handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        body_str = event.get('body') or '{}'
        # SNS sends JSON; handle both SNS subscription confirmation and notification
        body = json.loads(body_str)
        msg_type = event.get('headers', {}).get('x-amz-sns-message-type', '')

        # ── SNS subscription confirmation ──────────────────────────────────
        if msg_type == 'SubscriptionConfirmation':
            import urllib.request
            urllib.request.urlopen(body['SubscribeURL'])
            print('[alerts] SNS subscription confirmed.')
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': 'Confirmed'}

        # ── SNS notification ───────────────────────────────────────────────
        sns_message = body.get('Message', body_str)
        try:
            alert_data = json.loads(sns_message)
        except Exception:
            alert_data = {'raw': sns_message}

        alert_record = {
            'alertId':   str(uuid.uuid4()),
            'message':   alert_data.get('message', str(alert_data)),
            'severity':  alert_data.get('severity', 'warning'),
            'source':    alert_data.get('source', body.get('TopicArn', 'sns')),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'read':      False,
        }

        # Persist to DynamoDB
        alerts_tbl.put_item(Item=alert_record)
        print(f'[alerts] Stored alert: {alert_record["alertId"]}')

        # Broadcast to WebSocket clients
        _broadcast(alert_record)

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'alertId': alert_record['alertId']}),
        }

    except Exception as exc:
        print(f'[alerts] Unhandled error: {exc}')
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(exc)}),
        }
