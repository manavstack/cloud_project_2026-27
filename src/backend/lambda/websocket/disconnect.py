"""
websocket/disconnect.py — WebSocket $disconnect route
Federated Campus Energy Cloud

Called by API Gateway WebSocket API when a client disconnects.
Removes the connectionId from DynamoDB WsConnections table so stale
connections are not broadcast to.
"""

import os
import boto3

REGION   = os.environ.get('AWS_REGION', 'ap-south-1')
WS_TABLE = os.environ.get('WS_CONNECTIONS_TABLE', 'CampusEnergy-WsConnections')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table    = dynamodb.Table(WS_TABLE)


def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    try:
        table.delete_item(Key={'connectionId': connection_id})
        print(f'[ws/disconnect] Disconnected: {connection_id}')
        return {'statusCode': 200, 'body': 'Disconnected'}
    except Exception as exc:
        print(f'[ws/disconnect] Error: {exc}')
        return {'statusCode': 500, 'body': str(exc)}
