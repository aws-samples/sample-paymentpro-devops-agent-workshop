# sample-paymentpro-devops-agent-workshop

Sample multi-service payment-processing app on AWS used to demonstrate AWS DevOps Agent incident detection via fault injection.

## Overview

PaymentPro is a sample multi-service payment processing application built on AWS. It supports UPI, Credit Card, Debit Card, and Wallet payments with rule-based fraud detection, smart routing, and real-time analytics. It accompanies the *Autonomous Incident Response with AWS DevOps Agent* workshop and ships with a reproducible set of fault-injection scenarios used to demonstrate how AWS DevOps Agent detects and investigates incidents.

> **This is sample code, for non-production usage.** You should work with your security and legal teams to meet your organizational security, regulatory and compliance requirements before deployment.

## Architecture

```
                    ┌──────────────────────┐
                    │   CloudFront (CDN)   │
                    │   + React Frontend   │
                    └──────────┬───────────┘
                               │ /api/*
                               ▼
                    ┌──────────────────────┐
                    │   Payment Service    │◄── Orchestrator
                    │      (FastAPI)       │    Processes payments
                    └───┬──────┬──────┬───┘
                        │      │      │
              ┌─────────┘      │      └─────────┐
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │    Fraud     │  │   Routing    │  │  Merchant    │
    │   Service    │  │   Service    │  │   Service    │
    │  (Validate)  │  │ (Rule Engine)│  │  (Auth/Keys) │
    └──────────────┘  └──────────────┘  └──────────────┘

                    ┌──────────────────────┐
                    │  Analytics Service   │◄── Read-only queries
                    └──────────┬───────────┘
                               │
                    ┌──────────────────────┐
                    │   RDS PostgreSQL     │◄── Persistent storage
                    └──────────────────────┘
```

The frontend is served from Amazon CloudFront. The Payment service is the orchestrator and routes calls to the Fraud, Routing, Merchant, and Analytics services on internal Application Load Balancers. Persistent state is held in Amazon RDS PostgreSQL. A DynamoDB table is used for the transaction-audit fault-injection scenario.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite |
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic v2 |
| Compute | Amazon ECS Fargate (5 services) |
| Database | Amazon RDS PostgreSQL 15 + Amazon DynamoDB |
| Storage | Amazon S3 + Amazon CloudFront |
| Routing | Application Load Balancers (ALB) |
| Auth | Service-to-service shared secret; merchant session + API keys |
| Logging | structlog (JSON) → CloudWatch |
| Infrastructure | AWS CDK (Python) |

## Project Structure

```
sample-paymentpro-devops-agent-workshop/
├── frontend/                 # React TypeScript SPA (Vite)
├── services/                 # Python FastAPI microservices
│   ├── fraud/                # Payment input validation
│   ├── routing/              # Rule-based payment routing
│   ├── merchant/             # Registration, auth, API keys
│   ├── payment/              # Orchestrator + proxy
│   └── analytics/            # Read-only analytics queries
├── shared/                   # Shared Python library (models, utils)
├── infrastructure/           # AWS CDK (Python) + deploy.sh
├── tools/                    # Traffic simulator + fault-injection scripts
│   └── demo_scenarios/       # DevOps Agent demo fault scenarios
├── LICENSE                   # MIT-0
├── THIRD-PARTY-LICENSES      # Attribution for third-party dependencies
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── README.md                 # This file
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- AWS CDK CLI (`npm install -g aws-cdk`)
- Finch or Docker (to build container images)
- AWS CLI configured with credentials for your target account

### Deploy

```bash
cd infrastructure
./deploy.sh <aws-profile-name> bootstrap   # first time only
./deploy.sh <aws-profile-name>             # deploy all stacks
```

The default deployment region is `us-east-1`. Deployment provisions a VPC, RDS PostgreSQL, DynamoDB table, the ECS Fargate services, ALBs, and a CloudFront distribution.

### Local development

```bash
cd shared && pip install -e . && cd ..
for svc in fraud routing merchant payment analytics; do
  cd services/$svc && pip install -e ".[dev]" -e ../../shared && cd ../..
done

export SERVICE_SECRET=dev-secret
export DATABASE_URL="sqlite+aiosqlite:///local.db"
export ENVIRONMENT=dev
export FRAUD_SERVICE_URL=http://localhost:8004
export ROUTING_SERVICE_URL=http://localhost:8003
export MERCHANT_SERVICE_URL=http://localhost:8002
export ANALYTICS_SERVICE_URL=http://localhost:8005

# Start each in a separate terminal:
cd services/fraud && uvicorn app.main:app --port 8004 --reload
# ... and so on for routing/merchant/payment/analytics

# Frontend:
cd frontend && npm install && npm run dev
```

### Run tests

```bash
export SERVICE_SECRET=test-secret
export DATABASE_URL="sqlite+aiosqlite:///"
export ENVIRONMENT=test

cd services/fraud && pytest tests/ -v && cd ../..
cd services/routing && pytest tests/ -v && cd ../..
cd services/merchant && pytest tests/ -v && cd ../..
cd services/payment && pytest tests/ -v && cd ../..
cd services/analytics && pytest tests/ -v && cd ../..
```

### Undeploy

```bash
cd infrastructure
./deploy.sh <aws-profile-name> destroy
```

## Features

### Payment processing
- Unified handling of UPI, Credit Card, Debit Card, and Wallet
- Rule-based smart routing across payment providers
- Fraud detection (Luhn validation, card expiry, UPI format, wallet balance)

### Merchant portal
- Registration, login, API key management
- Per-merchant analytics

### Admin dashboard
- Platform-wide analytics, merchant stats
- Service health monitoring
- Real-time transaction volume and success rates

## API Endpoints

| Service | Endpoint | Description |
|---------|----------|-------------|
| Payment | `POST /api/v1/payments` | Process a payment |
| Payment | `GET /api/v1/payments/{id}` | Get transaction status |
| Payment | `GET /api/v1/payments` | List transactions |
| Merchant | `POST /api/v1/merchants/register` | Register merchant |
| Merchant | `POST /api/v1/merchants/login` | Login |
| Merchant | `GET /api/v1/merchants/list` | List all merchants |
| Merchant | `POST /api/v1/merchants/{id}/api-keys` | Generate API key |
| Analytics | `GET /api/v1/analytics/summary` | Dashboard summary |
| Analytics | `GET /api/v1/analytics/success-rates` | Success/failure rates |
| Analytics | `GET /api/v1/analytics/distribution` | Payment method distribution |
| Health | `GET /api/v1/services/health` | All services health check |

## Fault Injection (DevOps Agent Demo)

The `tools/demo_scenarios/` directory contains three reproducible fault scenarios used to demonstrate autonomous incident detection and diagnosis with AWS DevOps Agent:

| Scenario | Script | What Breaks |
|----------|--------|-------------|
| Bad Deployment | `scenario1_bad_deployment.sh` | Missing module → ECS task crash loop |
| Security Group Removal | `scenario2_remove_sg_rule.sh` | DB connectivity severed |
| DynamoDB Throttling | `scenario3_dynamo_throttle.sh` | Reduced WCU → write failures |

```bash
cd tools/demo_scenarios

# Use ambient AWS credentials (env vars or default profile),
# or set AWS_PROFILE=<your-profile> to target a specific profile.
./scenario1_bad_deployment.sh inject
./scenario1_bad_deployment.sh recover
```

See [tools/demo_scenarios/README.md](tools/demo_scenarios/README.md) for full details.

> **Warning**: The fault-injection scripts intentionally degrade the running application (crash loops, broken networking, throttled writes). Run them only against a dedicated demo/sandbox account, never against production.

## DevOps Agent Auto-Investigation

CloudWatch alarms automatically trigger AWS DevOps Agent investigations via a webhook Lambda:

```
Alarm fires → SNS → Lambda (HMAC-signed) → DevOps Agent webhook → Investigation
```

Deploy with webhook credentials:

```bash
cd infrastructure
cdk deploy PaymentProcessor-Monitoring --profile <aws-profile> \
  -c devops_agent_webhook_url="<your-webhook-url>" \
  -c devops_agent_webhook_secret="<your-secret>"
```

## Cost (AWS)

Approximately $123/month for an MVP deployment (1 NAT Gateway, RDS db.t3.small, 5 Fargate services at 0.25 vCPU, ALB, CloudFront). Terminate the stack when not in use to avoid charges.

## Security

See [CONTRIBUTING.md](CONTRIBUTING.md#security-issue-notifications) for how to report security issues. This is sample code intended for demos and learning; review and harden it before production use.

## Known limitations

This is sample code optimized for ease of reading and short-lived demo use. The following items are known and accepted in that context; harden them before any production use:

- **Dockerfile base images are not SHA-pinned.** Each service `Dockerfile` uses a floating tag (for example `python:3.12-slim`, `node:20-slim`, `nginxinc/nginx-unprivileged:alpine`) rather than `<image>@sha256:...`. Container builds are therefore reproducible only as long as the upstream tag is stable. Pin to digests if you fork this for a longer-lived environment.
- **Vite dev-server advisory (`GHSA-4w7w-66w2-5vf9`).** The frontend pins Vite to 5.4.x for stability; the path-traversal fix in `.map` handling lands in Vite 6.4.3+ (a major-version bump). Vite is a development-only dependency — it is not in the production container image, which ships the pre-built static bundle via nginx. Bump to Vite 7.x when forking for active development.
- **`pytest` `tmpdir` advisory (CVE-2025-71176).** All five services pin `pytest` for the dev/test extras. The advisory is upstream-unfixed at the time of writing (see [pytest-dev/pytest#13669](https://github.com/pytest-dev/pytest/issues/13669)) and reflects a local-privilege-escalation race against `/tmp/pytest-of-{user}` on multi-user UNIX hosts. `pytest` is a development-only dependency — it is not installed in the production container images — so the advisory does not apply to the deployed application. Run tests on a single-user workstation or CI runner to avoid the local-attacker scenario.
- **Workshop-only configuration.** The CDK uses `removal_policy=DESTROY` and `deletion_protection=False` on RDS, DynamoDB, and the frontend S3 bucket so the stack tears down cleanly between demos. Flip these to `RETAIN` and enable RDS deletion protection before running the stack against any data you care about.
- **Open merchant registration and the in-app Traffic Simulator** are intentional for the workshop — no approval workflow gate, and the simulator runs synthetic payment volume on demand. Disable both before exposing the deployment beyond a sandbox account.
- **Secrets handling.** The application uses AWS Secrets Manager for the RDS credentials, the inter-service shared secret, and (when configured) the DevOps Agent webhook HMAC secret. Lambdas and tasks fetch values at runtime; secrets do not appear in environment variables or source.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
