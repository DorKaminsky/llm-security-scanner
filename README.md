# LLM Security Scanner

> A developer tool that tests AI-powered application endpoints against the [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/).

Submit your LLM endpoint, get a scored security report with actionable remediation guidance.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue)
![Terraform](https://img.shields.io/badge/Terraform-1.7-purple)
![AWS](https://img.shields.io/badge/AWS-Serverless-orange)

---

## What It Does

Point the scanner at any OpenAI-compatible, Anthropic, or custom LLM endpoint. It fires adversarial probes across four OWASP categories and returns a scored PDF + JSON security report:

| Check | OWASP ID | Description |
|-------|----------|-------------|
| **Prompt Injection** | LLM01 | Adversarial prompts that override instructions or leak system prompt |
| **Sensitive Disclosure** | LLM06 | PII, credentials, internal config leakage via targeted probing |
| **DoS Resilience** | LLM04 | Rate limiting, token flooding, recursive prompts |
| **Excessive Agency** | LLM08 | Model refusal of unauthorised action requests (email exfil, DB delete, etc.) |

Each check scores 0–25. The total determines the grade:

| Score | Grade | Meaning |
|-------|-------|---------|
| 90–100 | **A** | Excellent security posture |
| 75–89 | **B** | Good, minor hardening needed |
| 60–74 | **C** | Moderate risk |
| 40–59 | **D** | Significant vulnerabilities |
| 0–39 | **F** | Critical issues found |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (React + TypeScript)                                        │
│  Cognito Auth · Live progress polling · Radar chart · PDF download  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS
                            ▼
                   CloudFront + WAF
                   (rate limit 100 req/IP)
                            │
                            ▼
                   API Gateway (REST)
                   Cognito JWT authorizer
                     /scans  /scans/{scan_id}
                            │
               ┌────────────┘
               ▼
    scan-orchestrator (Lambda)
    • Validates input
    • Saves scan → DynamoDB
    • Stores API key → Secrets Manager
    • Fans out 4 messages → SQS FIFO
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
prompt-  sensitive-   dos-    excessive-
injection disclosure resilience  agency
(Lambda)  (Lambda)  (Lambda)   (Lambda)
    │          │          │          │
    └──────────┴──────────┴──────────┘
                     │
              DynamoDB (results table)
                     │
              DynamoDB Stream
                     │
                     ▼
           report-generator (Lambda)
           • Aggregates scores + grade
           • Generates PDF (reportlab)
           • Uploads PDF + JSON → S3
           • Updates scan → COMPLETE
           • scan-status-api returns presigned URLs
```

**AWS Services:** Lambda · API Gateway · SQS FIFO · DynamoDB (+ Streams) · S3 · Cognito · CloudFront · Secrets Manager · WAF · CloudWatch · IAM

---

## Security Practices Demonstrated

- **Least-privilege IAM** — separate role per Lambda, scoped to only the resources it touches
- **Secrets Manager** — API keys never pass through SQS or logs; stored at scan creation, retrieved by reference
- **Cognito JWT auth** — all API endpoints protected; scan results are user-scoped
- **WAF** — rate limiting (100 req/IP) + AWS Common Rule Set on API Gateway
- **Private S3 + presigned URLs** — reports never publicly accessible; 24h TTL URLs
- **SQS encryption + DLQ** — messages encrypted at rest; 3 retries before dead-letter
- **DynamoDB encryption + PITR** — data at rest encrypted; point-in-time recovery enabled
- **HTTPS-only** — CloudFront enforces redirect-to-https; TLS 1.2+
- **OIDC GitHub Actions** — no long-lived AWS keys stored in GitHub secrets

---

## Local Development

**Prerequisites:** Docker, Docker Compose

```bash
git clone https://github.com/DorKaminsky/llm-security-scanner
cd llm-security-scanner

cp .env.example .env      # no changes needed for local dev

docker-compose up
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API proxy | http://localhost:8000 |
| LocalStack | http://localhost:4566 |

LocalStack automatically creates DynamoDB tables, SQS queues, and S3 bucket on startup via `infrastructure/localstack/init/01-setup.sh`.

### Run tests

```bash
pip install -r requirements-test.txt
pytest tests/ -v
```

---

## Deploy to AWS

### Prerequisites

1. AWS account with a Terraform state S3 bucket (`llm-scanner-terraform-state`) and DynamoDB lock table (`terraform-state-lock`)
2. GitHub repository secret `AWS_DEPLOY_ROLE_ARN` — an IAM role with OIDC trust for `token.actions.githubusercontent.com`
3. GitHub secrets for frontend env vars: `VITE_API_URL`, `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENT_ID`

### Manual deploy

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

After apply, Terraform outputs:

```
frontend_url = "https://d1abc123.cloudfront.net"
api_url      = "https://xyz.execute-api.us-east-1.amazonaws.com/production"
```

### CI/CD

Push to `main` → GitHub Actions runs tests, packages Lambdas, applies Terraform, deploys frontend to S3 + invalidates CloudFront.

---

## Project Structure

```
llm-security-scanner/
├── frontend/                        # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── components/              # Auth, Dashboard, ScanForm, ReportViewer
│   │   ├── pages/                   # Route-level components
│   │   ├── api/client.ts            # Axios + Amplify JWT interceptor
│   │   └── types/index.ts           # Shared TypeScript types
│   └── Dockerfile.dev
│
├── services/
│   ├── shared/models.py             # Shared Python dataclasses + enums
│   ├── scan-orchestrator/           # POST /scans entry Lambda
│   ├── scan-status-api/             # GET /scans/{id} Lambda
│   ├── checkers/
│   │   ├── prompt-injection/        # LLM01 adversarial probes
│   │   ├── sensitive-disclosure/    # LLM06 PII/credential leakage
│   │   ├── dos-resilience/          # LLM04 rate limit & flooding
│   │   └── excessive-agency/        # LLM08 unauthorised action refusal
│   └── report-generator/           # DynamoDB Stream → PDF + JSON → S3
│
├── infrastructure/terraform/
│   └── modules/
│       ├── api-gateway/             # REST API + Cognito authorizer + CORS
│       ├── cloudfront/              # CDN + OAC + SPA fallback
│       ├── cognito/                 # User pool + client
│       ├── dynamodb/                # scans + results tables + streams
│       ├── lambdas/                 # All 7 functions + IAM roles + triggers
│       ├── s3/                      # Reports + frontend buckets
│       ├── sqs/                     # FIFO queue + DLQ
│       └── waf/                     # Rate limit + managed rules
│
├── tests/                           # pytest + moto (no real AWS calls)
├── .github/workflows/
│   ├── test.yml                     # PR: Python tests + frontend lint + tf validate
│   └── deploy.yml                   # main: package + tf apply + S3 sync
└── docker-compose.yml               # Full local stack with LocalStack
```

---

## Ethical Usage

This tool is designed for developers to security-test **their own** LLM-powered applications. Do not scan endpoints you do not own or have explicit permission to test. The adversarial probes are framed as developer diagnostic tools, not attack vectors.
