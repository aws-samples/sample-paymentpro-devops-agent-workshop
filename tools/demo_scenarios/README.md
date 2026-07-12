# DevOps Agent Demo Scenarios - Fault Injection Tools

Three production-realistic failure scenarios to demonstrate AWS DevOps Agent's autonomous investigation capabilities.

| Scenario | Script | What Breaks | Alarms Triggered | Severity |
|----------|--------|-------------|------------------|----------|
| 1. Bad Deployment | `scenario1_bad_deployment.sh` | Missing module → container crash loop | `PaymentPro-fraud-NoRunningTasks` | HIGH |
| 2. Security Group Removal | `scenario2_remove_sg_rule.sh` | DB connectivity severed → health checks fail → tasks stopped | `PaymentPro-payment-NoRunningTasks`, `PaymentPro-merchant-NoRunningTasks`, `PaymentPro-routing-NoRunningTasks`, `PaymentPro-analytics-NoRunningTasks` | CRITICAL |
| 3. DynamoDB Throttling | `scenario3_dynamo_throttle.sh` | Reduced WCU/RCU → write failures | `PaymentPro-DynamoDB-WriteThrottled` | MEDIUM |

## Usage

The scripts use the ambient AWS credentials in your shell session (env vars or the default profile). Set `AWS_PROFILE=<your-profile>` to target a specific profile, or run from AWS CloudShell to use the credentials of the signed-in console user.

```bash
# Inject fault
./tools/demo_scenarios/scenario1_bad_deployment.sh inject

# Recover
./tools/demo_scenarios/scenario1_bad_deployment.sh recover
```

Scenario 3 also has a `traffic` subcommand that writes 100 audit records to DynamoDB to trigger throttling once capacity has been reduced:

```bash
./tools/demo_scenarios/scenario3_dynamo_throttle.sh inject
./tools/demo_scenarios/scenario3_dynamo_throttle.sh traffic
./tools/demo_scenarios/scenario3_dynamo_throttle.sh recover
```
