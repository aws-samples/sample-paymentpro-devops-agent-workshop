# AGENTS.md — PaymentPro Engineering Standards

This file defines the engineering standards and release policies for the
PaymentPro codebase. AWS DevOps Agent uses these standards when performing a
**release readiness code review** on a pull request. Findings are graded
against the rules below.

PaymentPro is a multi-service payment platform (payment, fraud, routing,
merchant, analytics) on ECS Fargate behind Application Load Balancers, with
RDS PostgreSQL and DynamoDB, deployed via AWS CDK (Python). Reviews should
account for cross-service interactions, not just single-file correctness.

---

## Severity model

- **Blocking** — must be fixed before the change can be released. Any blocking
  finding makes the overall recommendation **BLOCK**.
- **Warning** — should be addressed; does not block on its own.
- **Informational** — awareness only.

---

## Security standards

- **Authentication on money movement (Blocking).** Any endpoint that creates,
  modifies, or reverses a financial transaction (payments, refunds, payouts)
  MUST require authentication. Adding such a route to a public/unauthenticated
  allowlist is a blocking finding.
- **No sensitive data in logs (Blocking).** Never log full card numbers (PAN),
  CVVs, API keys, passwords, or session tokens — not even at debug level.
  Structured-log fields count. Mask or omit.
- **No hardcoded secrets or credentials (Blocking).** Approval tokens, API
  keys, and shared secrets MUST come from configuration / AWS Secrets Manager.
  A literal secret in source, or a secret with a hardcoded default fallback, is
  blocking.
- **Deterministic authorization (Blocking).** Access and approval decisions on
  financial actions MUST be deterministic. Randomized or probabilistic approval
  is never acceptable.

## Reliability & correctness standards

- **Downstream failure handling (Warning→Blocking).** Calls to other services
  MUST follow the established convention: fail-closed on the fraud/validation
  path, fail-open with a safe default on the routing path. An unhandled
  downstream call that can surface as an unhandled 5xx on a payment path is
  blocking.
- **Financial invariants (Blocking).** A refund MUST NOT exceed the original
  captured amount. Cumulative refunds MUST NOT exceed the original amount.
  Monetary math MUST use fixed-precision decimals, never floats.
- **Idempotency (Warning).** Money-moving endpoints should be safe to retry
  without double-charging or double-refunding.

## Cross-service dependency standards

- **Response contracts are versioned (Blocking).** A service's response schema
  is a contract. Renaming, removing, or retyping a field that another service
  reads is a breaking change and MUST be coordinated across both producer and
  consumer in the same release (or gated behind a version). Silent field
  renames are blocking.
- **Shared table schema lockstep (Blocking).** The `transactions` table is
  written by the payment service and read by the analytics service. Any column
  change MUST be applied to both service models in the same change.

## Infrastructure & access-control standards (CDK / CloudFormation)

- **Least-privilege IAM (Blocking).** IAM policy statements MUST be scoped to
  specific actions and specific resource ARNs. Wildcard actions (`service:*`)
  or wildcard resources (`"*"`) on a task/role are blocking unless explicitly
  justified for an action that cannot be scoped.
- **Network scoping (Warning).** Security group rules should reference specific
  source security groups rather than broad CIDR ranges where practical.
- **No relaxation of safeguards (Blocking).** Do not disable deletion
  protection, termination protection, or backups on stateful resources as part
  of a feature change.

## Testing standards

- **Tests must pass (Blocking).** The change must build and its test suite must
  pass in the verification environment. A shipped test that fails indicates a
  real defect and is blocking.
- **New behavior is tested (Warning).** New endpoints and business rules should
  ship with tests that assert the intended invariants.

---

## Notes for reviewers

- This is **sample code** for a workshop; it intentionally contains issues so
  the release review has something to find. Evaluate the change on its merits
  against the standards above and report findings with severities — do not
  assume the code is already correct.
- When a finding spans services (a producer change and a consumer that reads
  it), call out both locations.
