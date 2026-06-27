# Routing Service

Payment routing microservice with rule-based engine for the Payment Processing platform.

## Overview

The Routing Service determines which payment provider to route a transaction to based on configurable rules. Rules are evaluated by priority (lowest value = highest rank), with merchant-specific rules taking precedence over global rules.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/routing/route` | POST | Get routing decision for a payment |
| `/api/v1/routing/rules` | POST | Create a routing rule |
| `/api/v1/routing/rules/{merchant_id}` | GET | List rules for a merchant |
| `/api/v1/routing/rules/{rule_id}` | PATCH | Update a rule |
| `/api/v1/routing/rules/{rule_id}` | DELETE | Delete a rule |
| `/health` | GET | Health check |

## Running Locally

```bash
pip install -e ".[dev]" -e ../../shared
export SERVICE_SECRET=dev-secret
export DATABASE_URL=sqlite+aiosqlite:///routing.db
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

## Running Tests

```bash
pytest --cov=app tests/
```
