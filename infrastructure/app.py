#!/usr/bin/env python3
"""CDK application entry point for Payment Processor platform."""

import aws_cdk as cdk

from stacks.network_stack import NetworkStack
from stacks.database_stack import DatabaseStack
from stacks.services_stack import ServicesStack
from stacks.frontend_stack import FrontendStack
from stacks.simulator_stack import SimulatorStack
from stacks.monitoring_stack import MonitoringStack
from stacks.dynamodb_stack import DynamoDBStack

app = cdk.App()

# Uniform tags for cost tracking
TAGS = {
    "Project": "PaymentPro",
    "Environment": "production",
    "ManagedBy": "CDK",
    "Owner": "your-alias",
    "CostCenter": "payment-processor",
    "auto-delete": "no",
}

env = cdk.Environment(
    account=app.node.try_get_context("account") or None,
    region=app.node.try_get_context("region") or "us-east-1",
)

# Stack 1: VPC and networking
network = NetworkStack(app, "PaymentProcessor-Network", env=env)

# Stack 2: RDS PostgreSQL database
database = DatabaseStack(
    app, "PaymentProcessor-Database",
    vpc=network.vpc,
    env=env,
)

# Stack 3: ECS Fargate services (all 5 backend services)
services = ServicesStack(
    app, "PaymentProcessor-Services",
    vpc=network.vpc,
    database=database,
    env=env,
)

# Stack 4: S3 + CloudFront for frontend (with API proxy to Payment ALB)
frontend = FrontendStack(
    app, "PaymentProcessor-Frontend",
    payment_alb_dns=services.payment_alb_dns,
    env=env,
)

# Stack 5: Lambda + EventBridge for automated traffic generation
simulator = SimulatorStack(
    app, "PaymentProcessor-Simulator",
    payment_alb_dns=services.payment_alb_dns,
    env=env,
)

# Stack 6: CloudWatch Dashboard, Alarms, SNS, Webhook Lambda
monitoring = MonitoringStack(
    app, "PaymentProcessor-Monitoring",
    alb_full_names=services.alb_full_names,
    tg_full_names=services.tg_full_names,
    devops_agent_webhook_url=app.node.try_get_context("devops_agent_webhook_url") or "",
    devops_agent_webhook_secret=app.node.try_get_context("devops_agent_webhook_secret") or "",
    env=env,
)
monitoring.add_dependency(services)

# Stack 7: DynamoDB table for transaction audit (DevOps Agent demo scenario 3)
# Subscribes its throttle alarms to the same SNS topic as the other alarms so
# the DevOps Agent webhook fires for Lab 3 the same way it does for Labs 1 & 2.
dynamodb_table = DynamoDBStack(
    app, "PaymentProcessor-DynamoDB",
    alarm_topic_arn=monitoring.alarm_topic.topic_arn,
    env=env,
)
dynamodb_table.add_dependency(monitoring)

# Apply uniform tags to all stacks and resources
for stack in [network, database, services, frontend, simulator, monitoring, dynamodb_table]:
    for key, value in TAGS.items():
        cdk.Tags.of(stack).add(key, value)

app.synth()
