"""
forecast/handler.py — GET /forecast
Federated Campus Energy Cloud

Returns the latest predicted demand, 12-hour hourly bar data, peak reduction,
estimated savings, and active-client count from DynamoDB. Optionally calls a
SageMaker real-time inference endpoint if SAGEMAKER_ENDPOINT_NAME is set.

DynamoDB table: Forecasts
  PK: forecastId  (string, "latest" is always kept current by the aggregation Lambda)
  Attributes:
    predictedDemandKw    (number)
    peakReductionPct     (number)
    savingsINR           (number)
    activeClients        (string, e.g. "5 / 5")
    privacyEpsilonAvg    (number)
    hourlyBars           (list of numbers, 12 entries: 12h–23h)
    targetCeilingKw      (number)
    updatedAt            (string, ISO-8601)
"""

import json
import os
import boto3
from decimal import Decimal
from datetime import datetime, timezone

REGION         = os.environ.get('AWS_REGION', 'ap-south-1')
TABLE_NAME     = os.environ.get('FORECASTS_TABLE', 'CampusEnergy-Forecasts')
SM_ENDPOINT    = os.environ.get('SAGEMAKER_ENDPOINT_NAME', '')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table    = dynamodb.Table(TABLE_NAME)

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Content-Type': 'application/json',
}


def _decimal_to_float(obj):
    """Recursively convert Decimal values (from DynamoDB) to float for JSON."""
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def _call_sagemaker(endpoint_name: str) -> dict | None:
    """Call a SageMaker real-time endpoint and return parsed prediction."""
    try:
        sm = boto3.client('sagemaker-runtime', region_name=REGION)
        # Payload: last known demand + timestamp features (simplified)
        payload = json.dumps({'features': [datetime.now(timezone.utc).hour]})
        resp = sm.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=payload,
        )
        result = json.loads(resp['Body'].read())
        return result  # expected: {'predictedDemandKw': 842, 'hourlyBars': [...]}
    except Exception as exc:
        print(f'[SageMaker] Inference failed, falling back to DynamoDB: {exc}')
        return None


def handler(event, context):
    """Lambda entry point."""
    # OPTIONS pre-flight for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        # 1. Try SageMaker first (if endpoint configured)
        sm_result = _call_sagemaker(SM_ENDPOINT) if SM_ENDPOINT else None

        # 2. Read latest snapshot from DynamoDB
        resp = table.get_item(Key={'forecastId': 'latest'})
        item = resp.get('Item', {})

        if not item:
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'No forecast data found. Run seed_dynamodb.py first.'}),
            }

        data = _decimal_to_float(item)

        # 3. Merge SageMaker predictions if available
        if sm_result:
            data['predictedDemandKw'] = sm_result.get('predictedDemandKw', data.get('predictedDemandKw'))
            data['hourlyBars']        = sm_result.get('hourlyBars', data.get('hourlyBars'))
            data['source']            = 'sagemaker'
        else:
            data['source'] = 'dynamodb'

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(data),
        }

    except Exception as exc:
        print(f'[forecast] Unhandled error: {exc}')
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(exc)}),
        }
