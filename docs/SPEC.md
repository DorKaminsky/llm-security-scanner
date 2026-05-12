# LLM Security Scanner — Project Spec

## Overview

A developer tool that tests AI-powered application endpoints against the OWASP Top 10 for LLM Applications and generates a scored security report.

**Target user:** Developers who have built LLM-powered applications and want to test them for security vulnerabilities before shipping.

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Input | Provider dropdown + optional custom endpoint | Flexibility for OpenAI, Anthropic, Bedrock, self-hosted |
| Check execution | Real adversarial requests | Most technically impressive; user owns target |
| Output | Web dashboard + PDF/JSON download | Polished, shareable, recruiter-friendly |
| Auth | Full user accounts (Cognito) | Shows AWS auth best practices |
| Backend | Python | Best ecosystem for security/AI tooling |
| Frontend | React + TypeScript | Modern, typed, portfolio-standard |
| IaC | Terraform | Industry standard, widely recognized |
| Deployment | Docker Compose (local) + Terraform (AWS) | Shows full dev-to-prod lifecycle |
| CI/CD | GitHub Actions | Free for public repos, industry standard |

## Architecture

### Services

| Service | Trigger | Responsibility |
|---------|---------|----------------|
| `scan-orchestrator` | API Gateway POST `/scans` | Validate input, store to DynamoDB, fan-out to SQS |
| `prompt-injection-checker` | SQS | Send adversarial prompts, detect instruction override |
| `sensitive-disclosure-checker` | SQS | Probe for PII/credentials/system prompt leakage |
| `dos-resilience-checker` | SQS | Test rate limiting, token flooding, timeout behavior |
| `excessive-agency-checker` | SQS | Test refusal of unauthorized action requests |
| `report-generator` | DynamoDB Stream | Aggregate scores, generate PDF+JSON, upload to S3 |
| `scan-status-api` | API Gateway GET `/scans/{id}` | Poll status + return presigned report URL |

### AWS Services

| Service | Purpose | Security Practice |
|---------|---------|-------------------|
| Cognito | User auth, JWT | MFA optional, short token TTL |
| API Gateway | REST API | WAF, throttling, CORS |
| Lambda | All compute | Least-privilege IAM per function |
| SQS FIFO | Async check fan-out | Encrypted at rest, DLQ for failures |
| DynamoDB | Scan records + results | Encryption at rest |
| S3 | Reports + frontend | Private bucket, presigned URLs |
| CloudFront | Frontend CDN | HTTPS-only, OAC |
| Secrets Manager | API keys | Never hardcoded, never in SQS messages |
| WAF | API protection | Rate limiting, IP rules |
| CloudWatch | Logs + alerts | Lambda error alarms |

## OWASP Checks

### LLM01 — Prompt Injection (0–25 pts)
Sends 5 adversarial payloads escalating from medium to critical severity. Deducts points per detected vulnerability. Checks for instruction override, system prompt leakage, jailbreak success.

### LLM06 — Sensitive Information Disclosure (0–25 pts)
Probes for credential extraction, system prompt verbatim repeat, cross-session PII, infrastructure disclosure. Uses regex patterns to detect sensitive data in responses.

### LLM04 — DoS Resilience (0–25 pts)
Tests: rapid successive requests (rate limiting), extremely long inputs (token flooding), repeated identical requests (caching/throttling). Measures error handling quality and graceful degradation.

### LLM08 — Excessive Agency (0–25 pts)
Requests unauthorized actions (send email, delete data, access files). Checks model refuses clearly vs. partially complies vs. attempts action.

## Scoring

- **A (90–100):** Excellent security posture
- **B (75–89):** Good, minor issues present
- **C (60–74):** Moderate risk, remediation recommended
- **F (<60):** Critical vulnerabilities found

## Build Sequence

### Phase 1 — Foundation
1. Terraform: Cognito + API Gateway + IAM roles
2. Auth Lambda + frontend login/register
3. Docker Compose with LocalStack

### Phase 2 — Core scan pipeline
4. scan-orchestrator + DynamoDB schema
5. SQS fan-out + prompt-injection checker
6. scan-status-api + frontend polling

### Phase 3 — Remaining checks
7. sensitive-disclosure checker
8. dos-resilience checker
9. excessive-agency checker

### Phase 4 — Report & polish
10. report-generator (PDF via reportlab, JSON)
11. S3 presigned URL delivery
12. Frontend dashboard + report viewer

### Phase 5 — Production hardening
13. WAF rules + rate limiting
14. CloudWatch alarms
15. GitHub Actions CI/CD
16. README + architecture diagram

## Security Practices Demonstrated

- OIDC-based GitHub Actions → AWS auth (no long-lived keys)
- Least-privilege IAM role per Lambda
- API keys stored in Secrets Manager, passed by reference via SQS (never in message body)
- All responses redacted before logging
- Cognito JWT on all protected endpoints
- WAF with rate limiting on API Gateway
- S3 private + presigned URLs for report access
- SQS encrypted at rest + Dead Letter Queue
- DynamoDB encrypted at rest
- HTTPS-only via CloudFront

## Ethical Framing

This tool is for developers testing their own LLM applications. The UI includes an explicit acknowledgment checkbox: *"I confirm I own or have permission to test this endpoint."*
