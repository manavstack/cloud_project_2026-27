"""
export/handler.py — GET /export
Federated Campus Energy Cloud

Generates a time-limited S3 pre-signed URL so the authenticated dashboard
user can download the latest federation round CSV without exposing bucket
credentials to the browser.

The CSV file is written to S3 by the SageMaker aggregation job after each
federated round. This Lambda generates a 10-minute pre-signed GET URL.

Environment variables:
  EXPORT_BUCKET   — S3 bucket name (set by SAM template)
  EXPORT_KEY      — Object key of the CSV (default: exports/federation_latest.csv)
  URL_EXPIRY_SEC  — Pre-signed URL TTL in seconds (default: 600)
"""

import json
import os
import boto3
from botocore.exceptions import ClientError

REGION      = os.environ.get('AWS_REGION', 'ap-south-1')
BUCKET      = os.environ.get('EXPORT_BUCKET', '')
KEY         = os.environ.get('EXPORT_KEY', 'exports/federation_latest.csv')
EXPIRY_SEC  = int(os.environ.get('URL_EXPIRY_SEC', '600'))

s3 = boto3.client('s3', region_name=REGION)

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Content-Type': 'application/json',
}


def handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    if not BUCKET:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'EXPORT_BUCKET environment variable not set.'}),
        }

    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET, 'Key': KEY},
            ExpiresIn=EXPIRY_SEC,
        )
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'downloadUrl': url,
                'expiresInSeconds': EXPIRY_SEC,
                'filename': KEY.split('/')[-1],
            }),
        }
    except ClientError as exc:
        code = exc.response['Error']['Code']
        if code == 'NoSuchKey':
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Export file not found. Run a federation round first.'}),
            }
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(exc)}),
        }
