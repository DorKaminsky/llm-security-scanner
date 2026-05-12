import json
import logging
import os
from typing import Any

import boto3
from models import CheckType, ScanStatus

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))

SCANS_TABLE = os.environ["SCANS_TABLE"]
RESULTS_TABLE = os.environ["RESULTS_TABLE"]

CHECK_NAMES = {
    CheckType.PROMPT_INJECTION.value: "Prompt Injection (LLM01)",
    CheckType.SENSITIVE_DISCLOSURE.value: "Sensitive Information Disclosure (LLM06)",
    CheckType.DOS_RESILIENCE.value: "Model DoS Resilience (LLM04)",
    CheckType.EXCESSIVE_AGENCY.value: "Excessive Agency (LLM08)",
}


def handler(event: dict, context: Any) -> dict:
    scan_id = event["pathParameters"]["scan_id"]
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]

    scan = _get_scan(scan_id)
    if not scan:
        return _response(404, {"error": "Scan not found"})

    if scan.get("user_id") != user_id:
        return _response(403, {"error": "Forbidden"})

    results = _get_results(scan_id)
    checks_total = int(scan.get("checks_total", len(CheckType)))
    checks_complete = int(scan.get("checks_complete", 0))

    body = {
        "scan_id": scan_id,
        "status": scan.get("status", ScanStatus.PENDING),
        "provider": scan.get("provider"),
        "model": scan.get("model"),
        "created_at": scan.get("created_at"),
        "updated_at": scan.get("updated_at"),
        "progress": {
            "checks_complete": checks_complete,
            "checks_total": checks_total,
            "percent": int((checks_complete / checks_total) * 100) if checks_total else 0,
        },
        "checks": [
            {
                "check_id": ct.value,
                "check_name": CHECK_NAMES[ct.value],
                "status": results.get(ct.value, {}).get("status", "PENDING"),
                "score": results.get(ct.value, {}).get("score"),
                "findings_count": len(results.get(ct.value, {}).get("findings", [])),
                "duration_ms": results.get(ct.value, {}).get("duration_ms"),
            }
            for ct in CheckType
        ],
    }

    if scan.get("status") == ScanStatus.COMPLETE:
        body["total_score"] = scan.get("total_score")
        body["grade"] = scan.get("grade")
        body["report_pdf_url"] = scan.get("report_pdf_url")
        body["report_json_url"] = scan.get("report_json_url")

    return _response(200, body)


def _get_scan(scan_id: str) -> dict | None:
    table = dynamodb.Table(SCANS_TABLE)
    resp = table.get_item(Key={"scan_id": scan_id})
    return resp.get("Item")


def _get_results(scan_id: str) -> dict:
    table = dynamodb.Table(RESULTS_TABLE)
    results = {}
    for check_type in CheckType:
        resp = table.get_item(Key={"scan_id": scan_id, "check_type": check_type.value})
        item = resp.get("Item")
        if item:
            results[check_type.value] = item
    return results


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("FRONTEND_URL", "*"),
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, default=str),
    }
