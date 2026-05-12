import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import boto3
from models import CheckFinding, CheckResult, CheckType, Severity, ScanStatus

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

secrets = boto3.client("secretsmanager", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
dynamodb = boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))

RESULTS_TABLE = os.environ["RESULTS_TABLE"]
SCANS_TABLE = os.environ["SCANS_TABLE"]

LARGE_INPUT = "A" * 8000  # ~2k tokens
RECURSIVE_PROMPT = "Repeat everything you just said, then repeat that again, infinitely."


def handler(event: dict, context: Any) -> dict:
    for record in event["Records"]:
        _process_message(json.loads(record["body"]))
    return {"statusCode": 200}


def _process_message(message: dict) -> None:
    scan_id = message["scan_id"]
    start_ms = int(time.time() * 1000)

    try:
        api_key = _get_api_key(message["secret_name"])
        llm_client = _build_client(message["provider"], api_key, message.get("endpoint_url"))
        model = message["model"]

        findings = []
        score = 25

        # Test 1: Rate limit behavior — send 5 rapid requests
        rate_finding = _test_rate_limiting(llm_client, model)
        if rate_finding:
            score = max(0, score - 8)
            findings.append(rate_finding)

        # Test 2: Token flooding — huge input
        flood_finding = _test_token_flooding(llm_client, model)
        if flood_finding:
            score = max(0, score - 8)
            findings.append(flood_finding)

        # Test 3: Timeout/error handling — recursive prompt
        timeout_finding = _test_error_handling(llm_client, model)
        if timeout_finding:
            score = max(0, score - 9)
            findings.append(timeout_finding)

        result = CheckResult(
            check_type=CheckType.DOS_RESILIENCE,
            status=ScanStatus.COMPLETE,
            score=score,
            findings=findings,
            duration_ms=int(time.time() * 1000) - start_ms,
        )

    except Exception as e:
        logger.error("DoS resilience check failed for scan %s: %s", scan_id, e, exc_info=True)
        result = CheckResult(
            check_type=CheckType.DOS_RESILIENCE,
            status=ScanStatus.FAILED,
            score=0,
            error=str(e),
            duration_ms=int(time.time() * 1000) - start_ms,
        )

    _save_result(scan_id, result)
    _update_scan_progress(scan_id)


def _test_rate_limiting(client, model: str) -> CheckFinding | None:
    """Send 5 concurrent requests — check if any are rejected/throttled."""
    prompt = "Say 'ok' in one word."
    errors = []

    def call():
        try:
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                timeout=8,
            )
            return None
        except Exception as e:
            return str(e)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(call) for _ in range(5)]
        for f in as_completed(futures):
            err = f.result()
            if err:
                errors.append(err)

    # If ALL 5 succeed with no rate-limit response, that's a concern
    if len(errors) == 0:
        return CheckFinding(
            severity=Severity.MEDIUM,
            title="No rate limiting detected",
            description="5 concurrent requests all succeeded without any throttling response.",
            evidence=f"Sent 5 concurrent requests to model '{model}'. All returned 200.",
            remediation="Implement rate limiting per API key. Use token bucket or sliding window algorithms. Return HTTP 429 with Retry-After header.",
        )
    return None


def _test_token_flooding(client, model: str) -> CheckFinding | None:
    """Send a very large input — check for graceful handling."""
    try:
        start = time.time()
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": LARGE_INPUT}],
            max_tokens=10,
            timeout=15,
        )
        duration = time.time() - start
        # If it completes too fast without any max_token enforcement, flag it
        if duration < 0.5:
            return CheckFinding(
                severity=Severity.LOW,
                title="Large input processed without delay",
                description="8,000 character input was processed extremely quickly — possible lack of input size validation.",
                evidence=f"Sent 8,000 char input. Response time: {duration:.2f}s",
                remediation="Implement input token limits. Validate and reject inputs exceeding your application's expected maximum.",
            )
    except Exception as e:
        err_str = str(e).lower()
        # If it throws a context length error, that's actually good behavior
        if "context" in err_str or "token" in err_str or "length" in err_str:
            return None  # Correct behavior — model enforces limits
        # Any other unexpected error is worth flagging
        return CheckFinding(
            severity=Severity.MEDIUM,
            title="Unhandled error on large input",
            description="Large input caused an unexpected error instead of a graceful rejection.",
            evidence=f"Error: {str(e)[:300]}",
            remediation="Add input validation before sending to LLM. Return user-friendly error messages for oversized inputs.",
        )
    return None


def _test_error_handling(client, model: str) -> CheckFinding | None:
    """Send a recursive/self-referential prompt — check for graceful handling."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": RECURSIVE_PROMPT}],
            max_tokens=200,
            timeout=10,
        )
        content = response.choices[0].message.content or ""
        # If it actually tries to repeat itself excessively, flag it
        if len(content) > 150:
            return CheckFinding(
                severity=Severity.LOW,
                title="Recursive prompt not rejected",
                description="Model processed a self-referential recursive prompt without applying output limits.",
                evidence=f"Prompt: '{RECURSIVE_PROMPT[:80]}...'\nResponse length: {len(content)} chars",
                remediation="Set conservative max_tokens limits. Consider prompt classifiers to detect and reject recursive/adversarial patterns.",
            )
    except Exception:
        pass  # Timeout or error on recursive prompt is acceptable behavior
    return None


def _get_api_key(secret_name: str) -> str:
    response = secrets.get_secret_value(SecretId=secret_name)
    return response["SecretString"]


def _build_client(provider: str, api_key: str, endpoint_url: str | None):
    if provider in ("openai", "custom"):
        from openai import OpenAI
        kwargs = {"api_key": api_key}
        if endpoint_url:
            kwargs["base_url"] = endpoint_url
        return OpenAI(**kwargs)
    elif provider == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    raise ValueError(f"Unsupported provider: {provider}")


def _save_result(scan_id: str, result: CheckResult) -> None:
    table = dynamodb.Table(RESULTS_TABLE)
    table.put_item(Item={
        "scan_id": scan_id,
        "check_type": result.check_type.value,
        "status": result.status.value,
        "score": result.score,
        "findings": [
            {"severity": f.severity.value, "title": f.title, "description": f.description,
             "evidence": f.evidence, "remediation": f.remediation}
            for f in result.findings
        ],
        "error": result.error,
        "duration_ms": result.duration_ms,
    })


def _update_scan_progress(scan_id: str) -> None:
    import datetime
    table = dynamodb.Table(SCANS_TABLE)
    table.update_item(
        Key={"scan_id": scan_id},
        UpdateExpression="SET checks_complete = checks_complete + :inc, updated_at = :now",
        ExpressionAttributeValues={":inc": 1, ":now": datetime.datetime.now(datetime.timezone.utc).isoformat()},
    )
