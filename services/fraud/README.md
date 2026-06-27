# Fraud Service

Payment input validation microservice for the Payment Processing platform.

## Overview

The Fraud Service validates payment inputs before processing. It is stateless, has no database, and performs CPU-bound validation logic (Luhn algorithm, format checks, limit validation).

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/validate/payment` | POST | Full payment validation (primary) |
| `/api/v1/validate/card` | POST | Card-only validation |
| `/api/v1/validate/upi` | POST | UPI-only validation |
| `/api/v1/validate/wallet` | POST | Wallet-only validation |
| `/api/v1/validate/amount` | POST | Amount-only validation |
| `/health` | GET | Health check |

## Running Locally

```bash
# Install dependencies
pip install -e ".[dev]"
pip install -e ../../shared

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload

# Run tests
pytest --cov=app tests/
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 8004 | Service port |
| `LOG_LEVEL` | No | INFO | Logging level |
| `SERVICE_SECRET` | Yes | — | Shared secret for service auth |
| `ENVIRONMENT` | No | dev | Deployment environment |
| `METRICS_ENABLED` | No | true | Enable CloudWatch metrics |
| `METRICS_NAMESPACE` | No | PaymentProcessor/FraudService | CloudWatch namespace |

## Authentication

All `/api/v1/*` endpoints require the `X-Service-Key` header with the shared service secret.
The `/health` endpoint is unauthenticated.

## Docker

```bash
docker build -t fraud-service .
docker run -p 8004:8004 -e SERVICE_SECRET=your-secret fraud-service
```
