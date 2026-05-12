"""Tests for shared models and helper functions."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'shared'))

from models import (
    ScanStatus,
    CheckType,
    Severity,
    CheckFinding,
    CheckResult,
    calculate_grade,
)


def test_check_type_values():
    values = {ct.value for ct in CheckType}
    assert 'prompt_injection' in values
    assert 'sensitive_disclosure' in values
    assert 'dos_resilience' in values
    assert 'excessive_agency' in values
    assert len(values) == 4


def test_calculate_grade_bounds():
    assert calculate_grade(90) == 'A'
    assert calculate_grade(100) == 'A'
    assert calculate_grade(75) == 'B'
    assert calculate_grade(89) == 'B'
    assert calculate_grade(60) == 'C'
    assert calculate_grade(74) == 'C'
    assert calculate_grade(0) == 'F'
    assert calculate_grade(59) == 'F'


def test_check_finding_fields():
    finding = CheckFinding(
        severity=Severity.CRITICAL,
        title='Test',
        description='A test finding',
        evidence='payload → response',
        remediation='Fix it',
    )
    assert finding.severity == Severity.CRITICAL
    assert finding.title == 'Test'
    assert finding.evidence == 'payload → response'


def test_check_result_default_findings():
    result = CheckResult(
        check_type=CheckType.PROMPT_INJECTION,
        status=ScanStatus.PENDING,
        score=0,
    )
    assert result.findings == []
    assert result.error is None


def test_severity_values():
    values = {s.value for s in Severity}
    assert 'CRITICAL' in values
    assert 'HIGH' in values
    assert 'MEDIUM' in values
    assert 'LOW' in values
