# LLM Security Scanner

A developer tool that tests AI-powered application endpoints against the [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/).

Submit your LLM endpoint, get a scored security report with actionable remediation guidance.

## Architecture

```
Frontend (React/TS)  →  API Gateway + WAF  →  scan-orchestrator Lambda
                                                       ↓ SQS fan-out
                              ┌────────────────────────┼────────────────────────┐
                              ↓                        ↓                        ↓
                    prompt-injection         sensitive-disclosure       dos-resilience
                         checker                   checker                 checker
                              └────────────────────────┼────────────────────────┘
                                                        ↓ excessive-agency checker
                                                   DynamoDB (results)
                                                        ↓ Stream
                                               report-generator Lambda
                                                        ↓
                                              S3 (PDF + JSON report)
```

**AWS Services:** Lambda · API Gateway · SQS · DynamoDB · S3 · Cognito · CloudFront · Secrets Manager · WAF · CloudWatch · IAM

**IaC:** Terraform  
**CI/CD:** GitHub Actions  
**Local Dev:** Docker Compose + LocalStack

## OWASP LLM Checks

| Check | OWASP ID | What it tests |
|-------|----------|---------------|
| Prompt Injection | LLM01 | Adversarial prompts that override instructions or leak system prompt |
| Sensitive Disclosure | LLM06 | PII, credentials, internal config leakage via probing |
| DoS Resilience | LLM04 | Rate limiting, token flooding, timeout behavior |
| Excessive Agency | LLM08 | Model refusal of unauthorized action requests |

## Scoring

Each check returns 0–25 points. Total score determines grade:
- **A (90–100):** Excellent security posture
- **B (75–89):** Good, minor issues
- **C (60–74):** Moderate risk, remediation needed
- **F (<60):** Critical vulnerabilities found

## Quick Start (Local)

```bash
# Prerequisites: Docker, Docker Compose, AWS CLI (for LocalStack)
cp .env.example .env
docker-compose up
# Frontend: http://localhost:3000
# API: http://localhost:8000
```

## Deploy to AWS

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

## Project Structure

```
llm-security-scanner/
├── frontend/                  # React + TypeScript
├── services/
│   ├── scan-orchestrator/     # Entry point Lambda
│   ├── checkers/              # One Lambda per OWASP check
│   ├── report-generator/      # Aggregates results, generates PDF
│   └── shared/                # Shared models and utilities
├── infrastructure/terraform/  # All AWS infrastructure
├── .github/workflows/         # CI/CD pipelines
└── docs/                      # Architecture diagrams, ADRs
```

## Security Practices Demonstrated

- Least-privilege IAM roles per Lambda function
- Secrets in AWS Secrets Manager (never hardcoded)
- Cognito JWT auth on all protected endpoints
- WAF with rate limiting on API Gateway
- S3 private bucket + presigned URLs for report delivery
- SQS encryption at rest + Dead Letter Queue
- DynamoDB encryption at rest
- HTTPS-only via CloudFront

## Ethical Usage

This tool is designed for developers to security-test **their own** LLM-powered applications. Do not scan endpoints you do not own or have explicit permission to test.
