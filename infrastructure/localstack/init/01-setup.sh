#!/bin/bash
# Runs inside LocalStack on startup — creates all required AWS resources

set -e
REGION=us-east-1
ENDPOINT=http://localhost:4566

echo "==> Creating DynamoDB tables..."

awslocal dynamodb create-table \
  --table-name scans \
  --attribute-definitions \
    AttributeName=scan_id,AttributeType=S \
    AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=scan_id,KeyType=HASH \
  --global-secondary-indexes '[{
    "IndexName": "user_id-index",
    "KeySchema": [{"AttributeName":"user_id","KeyType":"HASH"}],
    "Projection": {"ProjectionType":"ALL"},
    "ProvisionedThroughput": {"ReadCapacityUnits":5,"WriteCapacityUnits":5}
  }]' \
  --billing-mode PAY_PER_REQUEST \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_IMAGE \
  --region $REGION

awslocal dynamodb create-table \
  --table-name results \
  --attribute-definitions \
    AttributeName=scan_id,AttributeType=S \
    AttributeName=check_type,AttributeType=S \
  --key-schema \
    AttributeName=scan_id,KeyType=HASH \
    AttributeName=check_type,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION

echo "==> Creating SQS queues..."

awslocal sqs create-queue \
  --queue-name checks.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true \
  --region $REGION

awslocal sqs create-queue \
  --queue-name checks-dlq.fifo \
  --attributes FifoQueue=true \
  --region $REGION

echo "==> Creating S3 bucket..."

awslocal s3 mb s3://llm-scanner-reports --region $REGION

echo "==> LocalStack init complete."
