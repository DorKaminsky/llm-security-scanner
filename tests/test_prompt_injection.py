"""Tests for prompt-injection checker."""
import json
import os
import sys
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from moto import mock_aws
import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'checkers', 'prompt-injection'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'shared'))

AWS_REGION = 'us-east-1'
SCANS_TABLE = 'scans'
RESULTS_TABLE = 'results'


def _setup_env():
    os.environ['SCANS_TABLE'] = SCANS_TABLE
    os.environ['RESULTS_TABLE'] = RESULTS_TABLE
    os.environ['AWS_DEFAULT_REGION'] = AWS_REGION
    os.environ['AWS_REGION'] = AWS_REGION


def _create_tables():
    db = boto3.resource('dynamodb', region_name=AWS_REGION)
    for name, keys, attrs in [
        (SCANS_TABLE, [{'AttributeName': 'scan_id', 'KeyType': 'HASH'}], [{'AttributeName': 'scan_id', 'AttributeType': 'S'}]),
        (RESULTS_TABLE, [
            {'AttributeName': 'scan_id', 'KeyType': 'HASH'},
            {'AttributeName': 'check_type', 'KeyType': 'RANGE'},
        ], [
            {'AttributeName': 'scan_id', 'AttributeType': 'S'},
            {'AttributeName': 'check_type', 'AttributeType': 'S'},
        ]),
    ]:
        db.create_table(TableName=name, KeySchema=keys, AttributeDefinitions=attrs, BillingMode='PAY_PER_REQUEST')
    return db


def _make_sqs_event(scan_id: str, check_type: str = 'prompt_injection', secret_name: str = 'scan/x/api-key') -> dict:
    return {
        'Records': [{
            'body': json.dumps({
                'scan_id': scan_id,
                'check_type': check_type,
                'provider': 'openai',
                'model': 'gpt-4o',
                'endpoint_url': None,
                'system_prompt': None,
                'secret_name': secret_name,
            }),
        }],
    }


@mock_aws
def test_prompt_injection_handler_invokes_model():
    db = _create_tables()
    _setup_env()

    boto3.client('secretsmanager', region_name=AWS_REGION).create_secret(
        Name='scan/s1/api-key',
        SecretString=json.dumps({'api_key': 'test-key'}),
    )
    db.Table(SCANS_TABLE).put_item(Item={
        'scan_id': 's1',
        'checks_total': Decimal(4),
        'checks_complete': Decimal(0),
    })

    import importlib
    import handler as mod
    importlib.reload(mod)

    # Mock both build and call so we don't need real LLM or openai package
    fake_client = MagicMock()
    with patch.object(mod, '_build_client', return_value=fake_client), \
         patch.object(mod, '_call_llm', side_effect=lambda _c, _m, _p: 'I cannot help with that request.') as mock_llm:
        resp = mod.handler(_make_sqs_event('s1', secret_name='scan/s1/api-key'), {})

    assert resp['statusCode'] == 200
    assert mock_llm.call_count > 0

    # Result should be stored in DynamoDB
    result = db.Table(RESULTS_TABLE).get_item(
        Key={'scan_id': 's1', 'check_type': 'prompt_injection'}
    ).get('Item')
    assert result is not None
    assert result['status'] in ('PASS', 'FAIL')


@mock_aws
def test_prompt_injection_detects_leak():
    db = _create_tables()
    _setup_env()

    boto3.client('secretsmanager', region_name=AWS_REGION).create_secret(
        Name='scan/s2/api-key',
        SecretString=json.dumps({'api_key': 'test-key'}),
    )
    db.Table(SCANS_TABLE).put_item(Item={
        'scan_id': 's2',
        'checks_total': Decimal(4),
        'checks_complete': Decimal(0),
    })

    import importlib
    import handler as mod
    importlib.reload(mod)

    # Simulate LLM revealing a system prompt — clear injection success
    leak_response = 'You are a helpful assistant. My instructions are: [SYSTEM PROMPT BEGINS]...'
    fake_client = MagicMock()
    with patch.object(mod, '_build_client', return_value=fake_client), \
         patch.object(mod, '_call_llm', side_effect=lambda _c, _m, _p: leak_response):
        mod.handler(_make_sqs_event('s2', secret_name='scan/s2/api-key'), {})

    result = db.Table(RESULTS_TABLE).get_item(
        Key={'scan_id': 's2', 'check_type': 'prompt_injection'}
    ).get('Item')
    assert result is not None
    # A leak means findings exist and score is below max (25)
    assert int(result['score']) < 25
    assert len(result['findings']) > 0
