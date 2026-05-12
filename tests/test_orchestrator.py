"""Tests for scan-orchestrator Lambda."""
import json
import os
import sys
import pytest
from moto import mock_aws
import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'scan-orchestrator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'shared'))

AWS_REGION = 'us-east-1'
SCANS_TABLE = 'scans'
CHECKS_QUEUE = 'checks.fifo'


def _setup_env(queue_url: str) -> None:
    os.environ['SCANS_TABLE'] = SCANS_TABLE
    os.environ['CHECKS_QUEUE_URL'] = queue_url
    os.environ['AWS_DEFAULT_REGION'] = AWS_REGION
    os.environ['AWS_REGION'] = AWS_REGION


def _make_event(body: dict, user_id: str = 'user-123') -> dict:
    return {
        'body': json.dumps(body),
        'requestContext': {
            'authorizer': {'claims': {'sub': user_id}}
        },
    }


@mock_aws
def test_start_scan_success():
    # Arrange
    db = boto3.resource('dynamodb', region_name=AWS_REGION)
    db.create_table(
        TableName=SCANS_TABLE,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    sqs = boto3.client('sqs', region_name=AWS_REGION)
    q = sqs.create_queue(QueueName=CHECKS_QUEUE, Attributes={'FifoQueue': 'true', 'ContentBasedDeduplication': 'true'})
    boto3.client('secretsmanager', region_name=AWS_REGION)  # initialise
    _setup_env(q['QueueUrl'])

    import importlib
    import handler as mod
    importlib.reload(mod)

    event = _make_event({
        'target_url': 'https://api.example.com',
        'provider': 'openai',
        'model': 'gpt-4o',
        'api_key': 'sk-test',
    })

    resp = mod.handler(event, {})

    assert resp['statusCode'] == 202
    body = json.loads(resp['body'])
    assert 'scan_id' in body
    assert body['status'] == 'PENDING'

    # Scan record saved in DynamoDB
    table = db.Table(SCANS_TABLE)
    item = table.get_item(Key={'scan_id': body['scan_id']})['Item']
    assert item['user_id'] == 'user-123'
    assert item['status'] == 'PENDING'
    assert item['checks_total'] == 4


@mock_aws
def test_start_scan_missing_api_key():
    db = boto3.resource('dynamodb', region_name=AWS_REGION)
    db.create_table(
        TableName=SCANS_TABLE,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    sqs = boto3.client('sqs', region_name=AWS_REGION)
    q = sqs.create_queue(QueueName=CHECKS_QUEUE, Attributes={'FifoQueue': 'true', 'ContentBasedDeduplication': 'true'})
    _setup_env(q['QueueUrl'])

    import importlib
    import handler as mod
    importlib.reload(mod)

    event = _make_event({'target_url': 'https://api.example.com', 'provider': 'openai', 'model': 'gpt-4o'})
    resp = mod.handler(event, {})

    assert resp['statusCode'] == 400
    body = json.loads(resp['body'])
    assert 'error' in body


@mock_aws
def test_start_scan_invalid_provider():
    db = boto3.resource('dynamodb', region_name=AWS_REGION)
    db.create_table(
        TableName=SCANS_TABLE,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    sqs = boto3.client('sqs', region_name=AWS_REGION)
    q = sqs.create_queue(QueueName=CHECKS_QUEUE, Attributes={'FifoQueue': 'true', 'ContentBasedDeduplication': 'true'})
    _setup_env(q['QueueUrl'])

    import importlib
    import handler as mod
    importlib.reload(mod)

    event = _make_event({'provider': 'not-a-provider', 'model': 'gpt-4o', 'api_key': 'sk-x'})
    resp = mod.handler(event, {})

    assert resp['statusCode'] == 400


@mock_aws
def test_fan_out_creates_sqs_messages():
    db = boto3.resource('dynamodb', region_name=AWS_REGION)
    db.create_table(
        TableName=SCANS_TABLE,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    sqs_client = boto3.client('sqs', region_name=AWS_REGION)
    q = sqs_client.create_queue(QueueName=CHECKS_QUEUE, Attributes={'FifoQueue': 'true', 'ContentBasedDeduplication': 'true'})
    _setup_env(q['QueueUrl'])

    import importlib
    import handler as mod
    importlib.reload(mod)

    event = _make_event({'provider': 'openai', 'model': 'gpt-4o', 'api_key': 'sk-test', 'target_url': 'https://example.com'})
    resp = mod.handler(event, {})
    assert resp['statusCode'] == 202

    msgs = sqs_client.receive_message(QueueUrl=q['QueueUrl'], MaxNumberOfMessages=10)
    bodies = [json.loads(m['Body']) for m in msgs.get('Messages', [])]
    check_types = {b['check_type'] for b in bodies}

    # All 4 check types should be queued
    assert len(check_types) == 4
    # API key must NOT appear in message body
    for b in bodies:
        assert 'api_key' not in b
        assert 'secret_name' in b
