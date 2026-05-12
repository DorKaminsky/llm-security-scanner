import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from models import CheckType, LLMProvider, LLMTarget, ScanRecord, ScanStatus

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
sqs = boto3.client("sqs", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
secrets = boto3.client("secretsmanager", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))

SCANS_TABLE = os.environ["SCANS_TABLE"]
CHECKS_QUEUE_URL = os.environ["CHECKS_QUEUE_URL"]


def handler(event: dict, context: Any) -> dict:
    try:
        body = json.loads(event.get("body", "{}"))
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]

        target = _parse_and_validate_target(body)
        scan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        _save_scan(scan_id, user_id, target, now)
        _fan_out_checks(scan_id, target)

        return {
            "statusCode": 202,
            "headers": _cors_headers(),
            "body": json.dumps({"scan_id": scan_id, "status": ScanStatus.PENDING}),
        }

    except ValueError as e:
        logger.warning("Validation error: %s", e)
        return {"statusCode": 400, "headers": _cors_headers(), "body": json.dumps({"error": str(e)})}
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return {"statusCode": 500, "headers": _cors_headers(), "body": json.dumps({"error": "Internal server error"})}


def _parse_and_validate_target(body: dict) -> LLMTarget:
    provider_str = body.get("provider")
    if not provider_str or provider_str not in [p.value for p in LLMProvider]:
        raise ValueError(f"Invalid provider. Must be one of: {[p.value for p in LLMProvider]}")

    model = body.get("model", "").strip()
    if not model:
        raise ValueError("model is required")

    api_key = body.get("api_key", "").strip()
    if not api_key:
        raise ValueError("api_key is required")

    return LLMTarget(
        provider=LLMProvider(provider_str),
        model=model,
        api_key=api_key,
        endpoint_url=body.get("endpoint_url"),
        system_prompt=body.get("system_prompt"),
    )


def _save_scan(scan_id: str, user_id: str, target: LLMTarget, now: str) -> None:
    table = dynamodb.Table(SCANS_TABLE)
    table.put_item(
        Item={
            "scan_id": scan_id,
            "user_id": user_id,
            "provider": target.provider.value,
            "model": target.model,
            "endpoint_url": target.endpoint_url,
            "status": ScanStatus.PENDING,
            "checks_total": len(CheckType),
            "checks_complete": 0,
            "created_at": now,
            "updated_at": now,
        }
    )


def _fan_out_checks(scan_id: str, target: LLMTarget) -> None:
    # Store API key in Secrets Manager — never pass it in SQS messages
    secret_name = f"scan/{scan_id}/api-key"
    secrets.create_secret(Name=secret_name, SecretString=target.api_key)

    for check_type in CheckType:
        sqs.send_message(
            QueueUrl=CHECKS_QUEUE_URL,
            MessageBody=json.dumps({
                "scan_id": scan_id,
                "check_type": check_type.value,
                "provider": target.provider.value,
                "model": target.model,
                "endpoint_url": target.endpoint_url,
                "system_prompt": target.system_prompt,
                "secret_name": secret_name,
            }),
            MessageGroupId=scan_id,  # FIFO group per scan
        )

    logger.info("Fanned out %d checks for scan %s", len(CheckType), scan_id)


def _cors_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": os.environ.get("FRONTEND_URL", "*"),
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }
