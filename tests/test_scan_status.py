"""Tests for scan-status-api Lambda."""
import json
import os
import sys
from decimal import Decimal
import pytest
from moto import mock_aws
import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'scan-status-api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'shared'))

AWS_REGION = 'us-east-1'
SCANS_TABLE = 'scans'
RESULTS_TABLE = 'results'


def _setup_env():
    os.environ['SCANS_TABLE'] = SCANS_TABLE
    os.environ['RESULTS_TABLE'] = RESULTS_TABLE
    os.environ['AWS_DEFAULT_REGION'] = AWS_REGION
    os.environ['AWS_REGION'] = AWS_REGION


def _make_event(scan_id: str, user_id: str = 'user-abc') -> dict:
    return {
        'pathParameters': {'scan_id': scan_id},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
    }


def _create_tables():
    db = boto3.resource('dynamodb', region_name=AWS_REGION)
    db.create_table(
        TableName=SCANS_TABLE,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    db.create_table(
        TableName=RESULTS_TABLE,
        KeySchema=[
            {'AttributeName': 'scan_id', 'KeyType': 'HASH'},
            {'AttributeName': 'check_type', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'scan_id', 'AttributeType': 'S'},
            {'AttributeName': 'check_type', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    return db


@mock_aws
def test_get_scan_returns_progress():
    db = _create_tables()
    _setup_env()

    # Seed a running scan
    db.Table(SCANS_TABLE).put_item(Item={
        'scan_id': 'scan-1',
        'user_id': 'user-abc',
        'status': 'RUNNING',
        'checks_total': Decimal(4),
        'checks_complete': Decimal(2),
        'provider': 'openai',
        'model': 'gpt-4o',
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:01:00+00:00',
    })

    import importlib
    import handler as mod
    importlib.reload(mod)

    resp = mod.handler(_make_event('scan-1'), {})
    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert body['status'] == 'RUNNING'
    assert body['progress']['percent'] == 50
    assert len(body['checks']) == 4


@mock_aws
def test_get_scan_not_found():
    _create_tables()
    _setup_env()

    import importlib
    import handler as mod
    importlib.reload(mod)

    resp = mod.handler(_make_event('nonexistent-scan'), {})
    assert resp['statusCode'] == 404


@mock_aws
def test_get_scan_forbidden_other_user():
    db = _create_tables()
    _setup_env()

    db.Table(SCANS_TABLE).put_item(Item={
        'scan_id': 'scan-2',
        'user_id': 'other-user',
        'status': 'PENDING',
        'checks_total': Decimal(4),
        'checks_complete': Decimal(0),
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
    })

    import importlib
    import handler as mod
    importlib.reload(mod)

    resp = mod.handler(_make_event('scan-2', user_id='user-abc'), {})
    assert resp['statusCode'] == 403


@mock_aws
def test_get_complete_scan_includes_report_urls():
    db = _create_tables()
    _setup_env()

    db.Table(SCANS_TABLE).put_item(Item={
        'scan_id': 'scan-3',
        'user_id': 'user-abc',
        'status': 'COMPLETE',
        'checks_total': Decimal(4),
        'checks_complete': Decimal(4),
        'total_score': Decimal(85),
        'grade': 'B',
        'report_pdf_url': 'https://s3.example.com/report.pdf',
        'report_json_url': 'https://s3.example.com/report.json',
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:02:00+00:00',
    })

    import importlib
    import handler as mod
    importlib.reload(mod)

    resp = mod.handler(_make_event('scan-3'), {})
    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert body['status'] == 'COMPLETE'
    assert body['grade'] == 'B'
    assert 'report_pdf_url' in body
