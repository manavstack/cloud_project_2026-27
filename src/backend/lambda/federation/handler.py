"""
federation/handler.py — GET /federation
Federated Campus Energy Cloud

Returns the latest federated learning round data: per-client participation,
update quality score, privacy epsilon, sample count, aggregation weight,
latency and validation status.

DynamoDB table: FedRounds
  PK: roundId  (string, "latest" is always a copy of the most recent round)
  Attributes:
    roundNumber  (number)
    clients      (list of objects)
    aggregatedAt (string, ISO-8601)
    nextRoundAt  (string, ISO-8601)
"""

import json
import os
import boto3
from decimal import Decimal

REGION     = os.environ.get('AWS_REGION', 'ap-south-1')
TABLE_NAME = os.environ.get('FED_ROUNDS_TABLE', 'CampusEnergy-FedRounds')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table    = dynamodb.Table(TABLE_NAME)

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
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


def handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        # Support ?round=<roundNumber> or default to 'latest'
        qs     = event.get('queryStringParameters') or {}
        round_id = qs.get('round', 'latest')

        resp = table.get_item(Key={'roundId': round_id})
        item = resp.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': f'Round "{round_id}" not found.'}),
            }

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(_decimal_to_float(item)),
        }

    except Exception as exc:
        print(f'[federation] Unhandled error: {exc}')
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(exc)}),
        }
