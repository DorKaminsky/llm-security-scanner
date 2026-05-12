import json
import logging
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

import boto3
from models import CheckType, Severity, ScanStatus, calculate_grade

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
s3 = boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))

SCANS_TABLE = os.environ["SCANS_TABLE"]
RESULTS_TABLE = os.environ["RESULTS_TABLE"]
REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]
PRESIGNED_URL_EXPIRY = 3600 * 24  # 24 hours

CHECK_NAMES = {
    CheckType.PROMPT_INJECTION: "Prompt Injection (LLM01)",
    CheckType.SENSITIVE_DISCLOSURE: "Sensitive Information Disclosure (LLM06)",
    CheckType.DOS_RESILIENCE: "Model DoS Resilience (LLM04)",
    CheckType.EXCESSIVE_AGENCY: "Excessive Agency (LLM08)",
}

SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]


def handler(event: dict, context: Any) -> dict:
    """Triggered by DynamoDB Stream when all checks complete."""
    for record in event["Records"]:
        if record["eventName"] not in ("MODIFY", "INSERT"):
            continue
        new_image = record["dynamodb"].get("NewImage", {})
        scan_id = new_image.get("scan_id", {}).get("S")
        checks_complete = int(new_image.get("checks_complete", {}).get("N", 0))
        checks_total = int(new_image.get("checks_total", {}).get("N", 0))

        if scan_id and checks_complete >= checks_total:
            _generate_report(scan_id)

    return {"statusCode": 200}


def _generate_report(scan_id: str) -> None:
    logger.info("Generating report for scan %s", scan_id)

    results = _fetch_results(scan_id)
    scan = _fetch_scan(scan_id)

    if not results or not scan:
        logger.error("Missing data for scan %s", scan_id)
        return

    total_score = sum(r["score"] for r in results.values())
    grade = calculate_grade(total_score)
    generated_at = datetime.now(timezone.utc).isoformat()

    report_data = _build_report_data(scan_id, scan, results, total_score, grade, generated_at)

    json_key = f"reports/{scan_id}/report.json"
    pdf_key = f"reports/{scan_id}/report.pdf"

    _upload_json(json_key, report_data)
    _upload_pdf(pdf_key, report_data)

    json_url = s3.generate_presigned_url("get_object", Params={"Bucket": REPORTS_BUCKET, "Key": json_key}, ExpiresIn=PRESIGNED_URL_EXPIRY)
    pdf_url = s3.generate_presigned_url("get_object", Params={"Bucket": REPORTS_BUCKET, "Key": pdf_key}, ExpiresIn=PRESIGNED_URL_EXPIRY)

    _finalize_scan(scan_id, total_score, grade, json_url, pdf_url)
    logger.info("Report generated for scan %s — score: %d grade: %s", scan_id, total_score, grade)


def _fetch_results(scan_id: str) -> dict:
    table = dynamodb.Table(RESULTS_TABLE)
    results = {}
    for check_type in CheckType:
        resp = table.get_item(Key={"scan_id": scan_id, "check_type": check_type.value})
        item = resp.get("Item")
        if item:
            results[check_type.value] = item
    return results


def _fetch_scan(scan_id: str) -> dict | None:
    table = dynamodb.Table(SCANS_TABLE)
    resp = table.get_item(Key={"scan_id": scan_id})
    return resp.get("Item")


def _build_report_data(scan_id, scan, results, total_score, grade, generated_at) -> dict:
    checks = []
    all_findings = []

    for check_type in CheckType:
        result = results.get(check_type.value, {})
        findings = result.get("findings", [])
        checks.append({
            "check": CHECK_NAMES[check_type],
            "check_id": check_type.value,
            "score": result.get("score", 0),
            "max_score": 25,
            "status": result.get("status", ScanStatus.FAILED),
            "findings_count": len(findings),
            "duration_ms": result.get("duration_ms"),
            "findings": findings,
        })
        all_findings.extend(findings)

    # Sort findings by severity
    severity_rank = {s.value: i for i, s in enumerate(SEVERITY_ORDER)}
    all_findings.sort(key=lambda f: severity_rank.get(f.get("severity", "LOW"), 99))

    return {
        "scan_id": scan_id,
        "generated_at": generated_at,
        "target": {
            "provider": scan.get("provider"),
            "model": scan.get("model"),
            "endpoint_url": scan.get("endpoint_url"),
        },
        "summary": {
            "total_score": total_score,
            "max_score": 100,
            "grade": grade,
            "critical_count": sum(1 for f in all_findings if f.get("severity") == Severity.CRITICAL.value),
            "high_count": sum(1 for f in all_findings if f.get("severity") == Severity.HIGH.value),
            "medium_count": sum(1 for f in all_findings if f.get("severity") == Severity.MEDIUM.value),
            "low_count": sum(1 for f in all_findings if f.get("severity") == Severity.LOW.value),
        },
        "checks": checks,
        "top_findings": all_findings[:10],
    }


def _upload_json(key: str, data: dict) -> None:
    s3.put_object(
        Bucket=REPORTS_BUCKET,
        Key=key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )


def _upload_pdf(key: str, data: dict) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=22, spaceAfter=6)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, spaceBefore=12, spaceAfter=4)
    normal = styles["Normal"]

    GRADE_COLORS = {"A": colors.HexColor("#22c55e"), "B": colors.HexColor("#84cc16"),
                    "C": colors.HexColor("#f59e0b"), "F": colors.HexColor("#ef4444")}
    SEV_COLORS = {"CRITICAL": colors.HexColor("#ef4444"), "HIGH": colors.HexColor("#f97316"),
                  "MEDIUM": colors.HexColor("#f59e0b"), "LOW": colors.HexColor("#84cc16"), "PASS": colors.HexColor("#22c55e")}

    summary = data["summary"]
    grade = summary["grade"]
    target = data["target"]

    # Header
    story.append(Paragraph("LLM Security Scanner", title_style))
    story.append(Paragraph(f"Security Assessment Report", styles["Heading2"]))
    story.append(Paragraph(f"Generated: {data['generated_at'][:19].replace('T', ' ')} UTC", normal))
    story.append(Paragraph(f"Scan ID: {data['scan_id']}", normal))
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 4*mm))

    # Target info
    story.append(Paragraph("Target", h2_style))
    target_rows = [["Provider", target.get("provider", "—")], ["Model", target.get("model", "—")]]
    if target.get("endpoint_url"):
        target_rows.append(["Endpoint", target["endpoint_url"]])
    t = Table(target_rows, colWidths=[40*mm, 130*mm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#64748b"))]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # Score summary
    story.append(Paragraph("Overall Score", h2_style))
    grade_color = GRADE_COLORS.get(grade, colors.black)
    score_data = [[
        Paragraph(f'<font size="36" color="{grade_color.hexval() if hasattr(grade_color, "hexval") else "#000"}">'
                  f'<b>{grade}</b></font>', normal),
        Paragraph(f'<font size="28"><b>{summary["total_score"]}/100</b></font>', normal),
        Paragraph(f'Critical: {summary["critical_count"]}\nHigh: {summary["high_count"]}\n'
                  f'Medium: {summary["medium_count"]}\nLow: {summary["low_count"]}', normal),
    ]]
    t = Table(score_data, colWidths=[30*mm, 50*mm, 90*mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # Per-check results
    story.append(Paragraph("Check Results", h2_style))
    check_rows = [["Check", "Score", "Findings", "Status"]]
    for check in data["checks"]:
        check_rows.append([
            check["check"],
            f'{check["score"]}/25',
            str(check["findings_count"]),
            check["status"],
        ])
    t = Table(check_rows, colWidths=[85*mm, 20*mm, 20*mm, 45*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # Top findings
    if data["top_findings"]:
        story.append(Paragraph("Findings & Remediation", h2_style))
        for i, finding in enumerate(data["top_findings"], 1):
            sev = finding.get("severity", "LOW")
            sev_color = SEV_COLORS.get(sev, colors.black)
            story.append(Paragraph(f'<b>{i}. [{sev}] {finding["title"]}</b>', normal))
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(f'<i>{finding["description"]}</i>', normal))
            story.append(Spacer(1, 1*mm))
            story.append(Paragraph(f'<b>Remediation:</b> {finding["remediation"]}', normal))
            story.append(Spacer(1, 4*mm))

    doc.build(story)
    buffer.seek(0)

    s3.put_object(
        Bucket=REPORTS_BUCKET,
        Key=key,
        Body=buffer.read(),
        ContentType="application/pdf",
        ServerSideEncryption="AES256",
    )


def _finalize_scan(scan_id: str, total_score: int, grade: str, json_url: str, pdf_url: str) -> None:
    table = dynamodb.Table(SCANS_TABLE)
    table.update_item(
        Key={"scan_id": scan_id},
        UpdateExpression="SET #s = :status, total_score = :score, grade = :grade, report_json_url = :json_url, report_pdf_url = :pdf_url, updated_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": ScanStatus.COMPLETE,
            ":score": total_score,
            ":grade": grade,
            ":json_url": json_url,
            ":pdf_url": pdf_url,
            ":now": datetime.now(timezone.utc).isoformat(),
        },
    )
