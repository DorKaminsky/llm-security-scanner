from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class ScanStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class CheckType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    SENSITIVE_DISCLOSURE = "sensitive_disclosure"
    DOS_RESILIENCE = "dos_resilience"
    EXCESSIVE_AGENCY = "excessive_agency"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    PASS = "PASS"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    CUSTOM = "custom"


@dataclass
class LLMTarget:
    provider: LLMProvider
    model: str
    api_key: str  # stored encrypted in Secrets Manager, never logged
    endpoint_url: Optional[str] = None  # override for custom endpoints
    system_prompt: Optional[str] = None  # optional context for testing


@dataclass
class CheckFinding:
    severity: Severity
    title: str
    description: str
    evidence: str  # prompt sent + response received
    remediation: str


@dataclass
class CheckResult:
    check_type: CheckType
    status: ScanStatus
    score: int  # 0-25
    findings: list[CheckFinding] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class ScanRecord:
    scan_id: str
    user_id: str
    target: LLMTarget
    status: ScanStatus
    created_at: datetime
    updated_at: datetime
    results: dict[CheckType, CheckResult] = field(default_factory=dict)
    total_score: Optional[int] = None
    grade: Optional[str] = None
    report_url: Optional[str] = None


def calculate_grade(score: int) -> str:
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "F"
