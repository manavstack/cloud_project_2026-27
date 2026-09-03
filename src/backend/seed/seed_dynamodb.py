"""
seed_dynamodb.py — Populate all DynamoDB tables with realistic initial data
Federated Campus Energy Cloud

Run locally (with LocalStack or real AWS credentials):
  python3 src/backend/seed/seed_dynamodb.py

Environment variables:
  AWS_REGION             (default: ap-south-1)
  DYNAMODB_ENDPOINT_URL  (optional: http://localhost:4566 for LocalStack)

Tables seeded:
  CampusEnergy-Forecasts    — latest 12-hour demand forecast
  CampusEnergy-FedRounds    — latest federation round with 5 client records
  CampusEnergy-Schedules    — active HVAC/EV/battery optimisation schedule
  CampusEnergy-Tariffs      — current time-of-use tariff plan
  CampusEnergy-Alerts       — one sample peak-demand alert
"""

import os
import json
import uuid
import boto3
from decimal import Decimal
from datetime import datetime, timezone, timedelta

REGION      = os.environ.get('AWS_REGION', 'ap-south-1')
ENDPOINT    = os.environ.get('DYNAMODB_ENDPOINT_URL', None)

kwargs = {'region_name': REGION}
if ENDPOINT:
    kwargs['endpoint_url'] = ENDPOINT

dynamodb = boto3.resource('dynamodb', **kwargs)

# ── Helper ──────────────────────────────────────────────────────────────────

def float_to_decimal(obj):
    """Recursively convert float to Decimal for DynamoDB."""
    if isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, float):
        return Decimal(str(obj))
    return obj


def seed_table(table_name: str, items: list[dict]):
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=float_to_decimal(item))
    print(f'  ✓  {table_name}: {len(items)} item(s) seeded.')


# ── Data ────────────────────────────────────────────────────────────────────

NOW = datetime.now(timezone.utc)

FORECASTS = [
    {
        'forecastId':          'latest',
        'predictedDemandKw':   842.0,
        'peakReductionPct':    24.2,
        'savingsINR':          8460.0,
        'activeClients':       '5 / 5',
        'privacyEpsilonAvg':   1.05,
        'targetCeilingKw':     900.0,
        # Bar heights (%) for hours 12–23
        'hourlyBars':          [36, 47, 58, 66, 72, 84, 97, 79, 63, 51, 41, 68],
        'source':              'dynamodb-seed',
        'updatedAt':           NOW.isoformat(),
    }
]

CLIENTS = [
    {'facility': 'Engineering Block', 'quality': 0.94, 'epsilon': 1.0, 'samples': 12480, 'weight': 0.32, 'latencyS': 1.2, 'status': 'Validated'},
    {'facility': 'Library',           'quality': 0.91, 'epsilon': 1.0, 'samples': 9320,  'weight': 0.28, 'latencyS': 0.9, 'status': 'Validated'},
    {'facility': 'Hostel Complex',    'quality': 0.88, 'epsilon': 1.2, 'samples': 14760, 'weight': 0.21, 'latencyS': 1.7, 'status': 'Validated'},
    {'facility': 'Science Labs',      'quality': 0.95, 'epsilon': 0.9, 'samples': 8100,  'weight': 0.11, 'latencyS': 0.8, 'status': 'Validated'},
    {'facility': 'Admin Block',       'quality': 0.89, 'epsilon': 1.1, 'samples': 6940,  'weight': 0.08, 'latencyS': 1.1, 'status': 'Validated'},
]

FED_ROUNDS = [
    {
        'roundId':      'latest',
        'roundNumber':  24,
        'clients':      CLIENTS,
        'aggregatedAt': NOW.isoformat(),
        'nextRoundAt':  (NOW + timedelta(minutes=5)).isoformat(),
        'allValidated': True,
    }
]

SCHEDULES = [
    {
        'scheduleId': 'active',
        'roundNumber': 24,
        'actions': [
            {'name': 'HVAC pre-cooling',  'description': 'Lower set-point 1°C before peak', 'time': '16:30 – 17:15', 'status': 'pending'},
            {'name': 'EV charging cap',   'description': 'Throttle to 40% during peak hour', 'time': '40% at 18:00', 'status': 'pending'},
            {'name': 'Battery dispatch',  'description': 'Discharge reserve to grid tie-in', 'time': '120 kW at 18:00', 'status': 'pending'},
        ],
        'approvedBy':  'seed-script',
        'approvedAt':  NOW.isoformat(),
        'status':      'approved',
    }
]

TARIFFS = [
    {
        'tariffId':        'current',
        'planName':        'ToU Campus Plan 2026-27',
        'currency':        'INR',
        'currentRateKwh':  6.50,
        'peakRateKwh':     12.40,
        'offPeakRateKwh':  3.20,
        'peakWindowStart': '18:00',
        'peakWindowEnd':   '19:00',
        'source':          'DynamoDB tariffs',
        'updatedAt':       NOW.isoformat(),
    }
]

ALERTS = [
    {
        'alertId':   str(uuid.uuid4()),
        'message':   'Peak demand forecast exceeds comfort threshold at 18:00 — HVAC pre-cooling recommended by 16:30.',
        'severity':  'warning',
        'source':    'seed',
        'timestamp': NOW.isoformat(),
        'read':      False,
    }
]

# ── Run ─────────────────────────────────────────────────────────────────────

def main():
    print(f'\nSeeding DynamoDB tables (region: {REGION}, endpoint: {ENDPOINT or "AWS default"})\n')
    seed_table('CampusEnergy-Forecasts',     FORECASTS)
    seed_table('CampusEnergy-FedRounds',     FED_ROUNDS)
    seed_table('CampusEnergy-Schedules',     SCHEDULES)
    seed_table('CampusEnergy-Tariffs',       TARIFFS)
    seed_table('CampusEnergy-Alerts',        ALERTS)
    print('\nAll tables seeded successfully.\n')


if __name__ == '__main__':
    main()
