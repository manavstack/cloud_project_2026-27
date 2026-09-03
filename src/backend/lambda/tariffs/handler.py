"""
tariffs/handler.py — GET /tariffs
Federated Campus Energy Cloud

Returns the current time-of-use tariff schedule from DynamoDB so the dashboard
can display live tariff windows and the optimisation Lambda can plan HVAC/EV loads.

DynamoDB table: Tariffs
  PK: tariffId  (string, "current" = active plan)
  Attributes:
    planName       (string)
    currency       (string, e.g. "INR")
    currentRateKwh (number)
    peakRateKwh    (number)
    offPeakRateKwh (number)
    peakWindowStart (string, "HH:MM")
    peakWindowEnd   (string, "HH:MM")
    source         (string, e.g. "DynamoDB tariffs")
    updatedAt      (string, ISO-8601)
"""

import json
import os
import boto3
from decimal import Decimal

REGION     = os.environ.get('AWS_REGION', 'ap-south-1')
TABLE_NAME = os.environ.get('TARIFFS_TABLE', 'CampusEnergy-Tariffs')

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
        resp = table.get_item(Key={'tariffId': 'current'})
        item = resp.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'No tariff data found. Run seed_dynamodb.py first.'}),
            }

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(_decimal_to_float(item)),
        }

    except Exception as exc:
        print(f'[tariffs] Unhandled error: {exc}')
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(exc)}),
        }
