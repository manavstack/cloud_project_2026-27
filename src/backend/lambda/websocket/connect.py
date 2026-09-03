"""
websocket/connect.py — WebSocket $connect route
Federated Campus Energy Cloud

Called by API Gateway WebSocket API when a client connects.
Stores the connectionId in DynamoDB WsConnections table so the
alerts Lambda can broadcast to all active clients.

DynamoDB table: WsConnections
  PK: connectionId  (string)
  Attributes:
    connectedAt (string, ISO-8601)
    principal   (string, Cognito username from authorizer)
"""

import json
import os
import boto3
from datetime import datetime, timezone

REGION   = os.environ.get('AWS_REGION', 'ap-south-1')
WS_TABLE = os.environ.get('WS_CONNECTIONS_TABLE', 'CampusEnergy-WsConnections')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table    = dynamodb.Table(WS_TABLE)


def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    # Cognito username injected by authorizer (if configured)
    authorizer    = event.get('requestContext', {}).get('authorizer', {})
    principal     = authorizer.get('principalId', 'anonymous')

    try:
        table.put_item(Item={
            'connectionId': connection_id,
            'connectedAt':  datetime.now(timezone.utc).isoformat(),
            'principal':    principal,
        })
        print(f'[ws/connect] Connected: {connection_id} ({principal})')
        return {'statusCode': 200, 'body': 'Connected'}
    except Exception as exc:
        print(f'[ws/connect] Error: {exc}')
        return {'statusCode': 500, 'body': str(exc)}
