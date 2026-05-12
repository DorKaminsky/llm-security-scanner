"""Shared pytest fixtures for all service tests."""
import json
import os
import sys
import pytest
import boto3
from moto import mock_aws

# Ensure services/shared is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'shared'))


AWS_REGION = 'us-east-1'
SCANS_TABLE = 'scans'
RESULTS_TABLE = 'results'
CHECKS_QUEUE = 'checks.fifo'
REPORTS_BUCKET = 'reports-test'
SECRET_NAME = 'scan/test-scan-id/api-key'


@pytest.fixture(scope='function')
def aws_credentials():
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = AWS_REGION
    os.environ['AWS_REGION'] = AWS_REGION


@pytest.fixture(scope='function')
def dynamodb(aws_credentials):
    with mock_aws():
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
        yield db


@pytest.fixture(scope='function')
def sqs(aws_credentials):
    with mock_aws():
        client = boto3.client('sqs', region_name=AWS_REGION)
        queue = client.create_queue(
            QueueName=CHECKS_QUEUE,
            Attributes={
                'FifoQueue': 'true',
                'ContentBasedDeduplication': 'true',
            },
        )
        yield client, queue['QueueUrl']


@pytest.fixture(scope='function')
def s3(aws_credentials):
    with mock_aws():
        client = boto3.client('s3', region_name=AWS_REGION)
        client.create_bucket(Bucket=REPORTS_BUCKET)
        yield client


@pytest.fixture(scope='function')
def secretsmanager(aws_credentials):
    with mock_aws():
        client = boto3.client('secretsmanager', region_name=AWS_REGION)
        client.create_secret(
            Name=SECRET_NAME,
            SecretString=json.dumps({'api_key': 'test-api-key-value'}),
        )
        yield client
