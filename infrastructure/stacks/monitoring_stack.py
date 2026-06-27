"""CloudWatch Dashboard, Alarms, SNS, and DevOps Agent Webhook Lambda."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct


class MonitoringStack(Stack):
    """CloudWatch Dashboard, Alarms, SNS topic, and DevOps Agent webhook Lambda.

    Deploys everything needed for observability and auto-investigation:
    - CloudWatch Dashboard with all service metrics
    - 24 CloudWatch Alarms (CPU, Memory, ALB, RDS, Lambda, NAT)
    - SNS Topic for alarm notifications
    - Lambda function to forward alarms to DevOps Agent webhook
    - S3 bucket for ALB access logs
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        devops_agent_webhook_url: str = "",
        devops_agent_webhook_secret: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        services = ["fraud", "routing", "merchant", "payment", "analytics"]

        # =============================================
        # SNS Topic for Alarm Notifications
        # =============================================
        alarm_topic = sns.Topic(
            self, "AlarmTopic",
            topic_name="PaymentPro-Alarms",
            display_name="PaymentPro CloudWatch Alarms",
        )

        # =============================================
        # DevOps Agent Webhook Secret (in Secrets Manager)
        # =============================================
        # The webhook URL is treated as configuration (env var); the shared
        # secret is treated as a credential and stored in Secrets Manager.
        # When `devops_agent_webhook_secret` is empty, no secret is created
        # and the Lambda short-circuits (see lambda/devops_agent_webhook.py).
        webhook_secret_arn = ""
        if devops_agent_webhook_secret:
            webhook_secret = secretsmanager.Secret(
                self, "DevOpsAgentWebhookSecret",
                secret_name="payment-processor/devops-agent-webhook-secret",
                description="HMAC-SHA256 shared secret used to sign DevOps Agent webhook payloads.",
                secret_string_value=cdk.SecretValue.unsafe_plain_text(devops_agent_webhook_secret),
            )
            webhook_secret_arn = webhook_secret.secret_arn

        # =============================================
        # DevOps Agent Webhook Lambda
        # =============================================
        webhook_lambda = _lambda.Function(
            self, "DevOpsAgentWebhook",
            function_name="PaymentPro-DevOpsAgent-Webhook",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="devops_agent_webhook.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "WEBHOOK_URL": devops_agent_webhook_url,
                # Lambda reads the secret value at invocation time from
                # Secrets Manager via this ARN. Empty string ⇒ no-op handler.
                "WEBHOOK_SECRET_ARN": webhook_secret_arn,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Forwards CloudWatch Alarms to AWS DevOps Agent for auto-investigation",
        )

        # Grant Lambda permission to read CloudWatch
        webhook_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["cloudwatch:DescribeAlarms", "cloudwatch:DescribeAlarmHistory"],
            resources=["*"],
        ))

        # Grant Lambda permission to read the webhook secret (only when configured)
        if devops_agent_webhook_secret:
            webhook_secret.grant_read(webhook_lambda)

        # Subscribe Lambda to SNS topic
        alarm_topic.add_subscription(sns_subs.LambdaSubscription(webhook_lambda))

        # =============================================
        # ALB Access Logs Bucket
        # =============================================
        access_logs_bucket = s3.Bucket(
            self, "AlbAccessLogs",
            bucket_name=None,  # Auto-generated
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(30)),
            ],
        )

        # Allow ELB to write access logs (us-east-1 ELB account: 127311923021)
        access_logs_bucket.add_to_resource_policy(iam.PolicyStatement(
            principals=[iam.AccountPrincipal("127311923021")],
            actions=["s3:PutObject"],
            resources=[access_logs_bucket.arn_for_objects("*")],
        ))

        # =============================================
        # CloudWatch Dashboard
        # =============================================
        dashboard = cw.Dashboard(
            self, "PaymentProDashboard",
            dashboard_name="PaymentPro-Operations",
        )

        # CPU Utilization per service
        cpu_widgets = []
        for svc in services:
            cpu_widgets.append(
                cw.GraphWidget(
                    title=f"{svc.capitalize()} CPU",
                    left=[
                        cw.Metric(
                            namespace="AWS/ECS",
                            metric_name="CPUUtilization",
                            dimensions_map={
                                "ClusterName": "payment-processor",
                                "ServiceName": f"{svc}-service",
                            },
                            statistic="Average",
                            period=Duration.minutes(1),
                        )
                    ],
                    width=4, height=6,
                )
            )
        dashboard.add_widgets(*cpu_widgets)

        # Memory Utilization per service
        mem_widgets = []
        for svc in services:
            mem_widgets.append(
                cw.GraphWidget(
                    title=f"{svc.capitalize()} Memory",
                    left=[
                        cw.Metric(
                            namespace="AWS/ECS",
                            metric_name="MemoryUtilization",
                            dimensions_map={
                                "ClusterName": "payment-processor",
                                "ServiceName": f"{svc}-service",
                            },
                            statistic="Average",
                            period=Duration.minutes(1),
                        )
                    ],
                    width=4, height=6,
                )
            )
        dashboard.add_widgets(*mem_widgets)

        # ALB Metrics
        dashboard.add_widgets(
            cw.GraphWidget(title="ALB Request Count", left=[cw.Metric(namespace="AWS/ApplicationELB", metric_name="RequestCount", statistic="Sum", period=Duration.minutes(1))], width=8, height=6),
            cw.GraphWidget(title="ALB Response Time", left=[cw.Metric(namespace="AWS/ApplicationELB", metric_name="TargetResponseTime", statistic="Average", period=Duration.minutes(1))], width=8, height=6),
            cw.GraphWidget(title="ALB 5xx Errors", left=[cw.Metric(namespace="AWS/ApplicationELB", metric_name="HTTPCode_Target_5XX_Count", statistic="Sum", period=Duration.minutes(1))], width=8, height=6),
        )

        # RDS Metrics
        dashboard.add_widgets(
            cw.GraphWidget(title="RDS CPU", left=[cw.Metric(namespace="AWS/RDS", metric_name="CPUUtilization", statistic="Average", period=Duration.minutes(1))], width=8, height=6),
            cw.GraphWidget(title="RDS Connections", left=[cw.Metric(namespace="AWS/RDS", metric_name="DatabaseConnections", statistic="Maximum", period=Duration.minutes(1))], width=8, height=6),
            cw.GraphWidget(title="RDS IOPS", left=[cw.Metric(namespace="AWS/RDS", metric_name="ReadIOPS", statistic="Average", period=Duration.minutes(1)), cw.Metric(namespace="AWS/RDS", metric_name="WriteIOPS", statistic="Average", period=Duration.minutes(1))], width=8, height=6),
        )

        # Lambda & NAT
        dashboard.add_widgets(
            cw.GraphWidget(title="Traffic Generator Lambda", left=[cw.Metric(namespace="AWS/Lambda", metric_name="Invocations", dimensions_map={"FunctionName": "payment-traffic-generator"}, statistic="Sum", period=Duration.minutes(5)), cw.Metric(namespace="AWS/Lambda", metric_name="Errors", dimensions_map={"FunctionName": "payment-traffic-generator"}, statistic="Sum", period=Duration.minutes(5))], width=12, height=6),
            cw.GraphWidget(title="NAT Gateway Traffic", left=[cw.Metric(namespace="AWS/NATGateway", metric_name="BytesOutToDestination", statistic="Sum", period=Duration.minutes(1))], width=12, height=6),
        )

        # =============================================
        # CloudWatch Alarms (all connected to SNS)
        # =============================================

        # ECS CPU Alarms
        for svc in services:
            cw.Alarm(self, f"{svc.capitalize()}CpuAlarm", alarm_name=f"PaymentPro-{svc}-HighCPU", alarm_description=f"{svc}-service CPU > 70%", metric=cw.Metric(namespace="AWS/ECS", metric_name="CPUUtilization", dimensions_map={"ClusterName": "payment-processor", "ServiceName": f"{svc}-service"}, statistic="Average", period=Duration.minutes(1)), threshold=70, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # ECS Memory Alarms
        for svc in services:
            cw.Alarm(self, f"{svc.capitalize()}MemAlarm", alarm_name=f"PaymentPro-{svc}-HighMemory", alarm_description=f"{svc}-service Memory > 80%", metric=cw.Metric(namespace="AWS/ECS", metric_name="MemoryUtilization", dimensions_map={"ClusterName": "payment-processor", "ServiceName": f"{svc}-service"}, statistic="Average", period=Duration.minutes(1)), threshold=80, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # ECS No Running Tasks Alarms
        for svc in services:
            cw.Alarm(self, f"{svc.capitalize()}NoTasksAlarm", alarm_name=f"PaymentPro-{svc}-NoRunningTasks", alarm_description=f"{svc}-service has 0 running tasks", metric=cw.Metric(namespace="ECS/ContainerInsights", metric_name="RunningTaskCount", dimensions_map={"ClusterName": "payment-processor", "ServiceName": f"{svc}-service"}, statistic="Average", period=Duration.minutes(1)), threshold=1, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.LESS_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # ALB Alarms
        cw.Alarm(self, "Alb5xxAlarm", alarm_name="PaymentPro-ALB-High5xxErrors", alarm_description="ALB > 5 5xx errors/min", metric=cw.Metric(namespace="AWS/ApplicationELB", metric_name="HTTPCode_Target_5XX_Count", statistic="Sum", period=Duration.minutes(1)), threshold=5, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        cw.Alarm(self, "AlbLatencyAlarm", alarm_name="PaymentPro-ALB-HighLatency", alarm_description="ALB p95 latency > 1s", metric=cw.Metric(namespace="AWS/ApplicationELB", metric_name="TargetResponseTime", statistic="p95", period=Duration.minutes(1)), threshold=1, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # RDS Alarms
        cw.Alarm(self, "RdsCpuAlarm", alarm_name="PaymentPro-RDS-HighCPU", alarm_description="RDS CPU > 70%", metric=cw.Metric(namespace="AWS/RDS", metric_name="CPUUtilization", statistic="Average", period=Duration.minutes(1)), threshold=70, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        cw.Alarm(self, "RdsConnectionsAlarm", alarm_name="PaymentPro-RDS-HighConnections", alarm_description="RDS connections > 30", metric=cw.Metric(namespace="AWS/RDS", metric_name="DatabaseConnections", statistic="Maximum", period=Duration.minutes(1)), threshold=30, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        cw.Alarm(self, "RdsIopsAlarm", alarm_name="PaymentPro-RDS-HighIOPS", alarm_description="RDS IOPS > 500", metric=cw.Metric(namespace="AWS/RDS", metric_name="ReadIOPS", statistic="Average", period=Duration.minutes(1)), threshold=500, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # =============================================
        # Outputs
        # =============================================
        CfnOutput(self, "DashboardUrl", value=f"https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=PaymentPro-Operations")
        CfnOutput(self, "SnsTopicArn", value=alarm_topic.topic_arn)
        CfnOutput(self, "WebhookLambdaName", value=webhook_lambda.function_name)
        CfnOutput(self, "AccessLogsBucket", value=access_logs_bucket.bucket_name)
