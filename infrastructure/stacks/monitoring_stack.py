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
        alb_full_names: dict[str, str] | None = None,
        tg_full_names: dict[str, str] | None = None,
        db_instance_identifier: str | None = None,
        devops_agent_webhook_url: str = "",
        devops_agent_webhook_secret: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # alb_full_names is keyed by short service name ("fraud", "routing",
        # "merchant", "analytics", "payment") and holds the CloudWatch
        # LoadBalancer dimension value (e.g. "app/Paymen-Payme-.../abc")
        # for that service's ALB. Widgets and alarms require this dimension
        # or they resolve to nothing.
        alb_full_names = alb_full_names or {}
        # tg_full_names holds the CloudWatch TargetGroup dimension value.
        # HealthyHostCount and UnHealthyHostCount only publish when queried
        # with BOTH LoadBalancer AND TargetGroup dimensions.
        tg_full_names = tg_full_names or {}

        services = ["fraud", "routing", "merchant", "payment", "analytics"]

        # Collect every alarm we create in this stack so we can render an
        # AlarmStatusWidget at the top of the dashboard. Grouped so we can
        # show one "row" per concern (ECS / ALB / RDS / DynamoDB) later.
        alarms_by_group: dict[str, list[cw.IAlarm]] = {
            "ECS": [],
            "ALB": [],
            "RDS": [],
            "DynamoDB": [],
        }

        # =============================================
        # SNS Topic for Alarm Notifications
        # =============================================
        # Exposed as self.alarm_topic so other stacks (e.g. DynamoDBStack)
        # can subscribe their alarms to the same fan-out topic.
        self.alarm_topic = sns.Topic(
            self, "AlarmTopic",
            topic_name="PaymentPro-Alarms",
            display_name="PaymentPro CloudWatch Alarms",
        )
        alarm_topic = self.alarm_topic  # local alias to keep existing widget/alarm calls compact

        # =============================================
        # DevOps Agent Webhook Secret (in Secrets Manager)
        # =============================================
        # The webhook URL is stored as a Lambda env var.
        # The HMAC shared secret is stored in Secrets Manager.
        #
        # Deploy with placeholder values initially. After creating your
        # DevOps Agent space and webhook, update them:
        #   - Lambda console → PaymentPro-DevOpsAgent-Webhook → Environment variables → WEBHOOK_URL
        #   - Secrets Manager → payment-processor/devops-agent-webhook-secret → edit value
        #
        # Or re-deploy with:
        #   cdk deploy PaymentProcessor-Monitoring \
        #     -c devops_agent_webhook_url="<your-url>" \
        #     -c devops_agent_webhook_secret="<your-secret>"

        effective_webhook_url = devops_agent_webhook_url or "PLACEHOLDER_UPDATE_AFTER_DEVOPS_AGENT_SETUP"
        effective_webhook_secret = devops_agent_webhook_secret or "PLACEHOLDER_UPDATE_AFTER_DEVOPS_AGENT_SETUP"

        webhook_secret = secretsmanager.Secret(
            self, "DevOpsAgentWebhookSecret",
            secret_name="payment-processor/devops-agent-webhook-secret",
            description="HMAC-SHA256 shared secret used to sign DevOps Agent webhook payloads. Update this value after creating your DevOps Agent webhook.",
            secret_string_value=cdk.SecretValue.unsafe_plain_text(effective_webhook_secret),
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
                "WEBHOOK_URL": effective_webhook_url,
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

        # Grant Lambda permission to read the webhook secret
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

        # -----------------------------------------------------------------
        # Row 1: Header / usage guide (renders at top of dashboard)
        # -----------------------------------------------------------------
        dashboard.add_widgets(
            cw.TextWidget(
                markdown=(
                    "# PaymentPro Operations\n\n"
                    "Signals used across the three DevOps Agent lab scenarios:\n\n"
                    "- **Lab 1 (bad deployment):** *ECS Running Tasks* row — watch `fraud-service` drop to 0.\n"
                    "- **Lab 2 (SG removal):** *ECS Running Tasks* + *ALB Healthy Hosts (per service ALB)* + *ALB ELB-generated 5xx* — 4 services lose DB, tasks stopped, healthy hosts fall, ELB-generated 5xx spikes on each affected ALB.\n"
                    "- **Lab 3 (DynamoDB throttle):** *DynamoDB throttled requests* + *DynamoDB capacity* rows — writes rejected, `WriteThrottleEvents > 0`.\n"
                    "- The **Alarm Status** widgets at the *bottom* of the dashboard are the single-pane summary — anything red there is what the DevOps Agent picks up. Each of the 5 services has its own ALB, so ALB alarms are per-service (e.g. `PaymentPro-ALB-payment-High5xxErrors`).\n"
                ),
                width=24, height=5,
            )
        )

        # -----------------------------------------------------------------
        # Row 2 (rendered): ECS Running Task Count per service (Labs 1 & 2)
        # -----------------------------------------------------------------
        # RunningTaskCount is the metric that goes to zero when ECS stops
        # the tasks in a crash loop (Lab 1) or after the circuit-breaker
        # stops them (Lab 2). It's the fastest visual signal in either lab.
        running_task_widgets = []
        for svc in services:
            running_task_widgets.append(
                cw.GraphWidget(
                    title=f"{svc.capitalize()} Running Tasks",
                    left=[
                        cw.Metric(
                            namespace="ECS/ContainerInsights",
                            metric_name="RunningTaskCount",
                            dimensions_map={
                                "ClusterName": "payment-processor",
                                "ServiceName": f"{svc}-service",
                            },
                            statistic="Average",
                            period=Duration.minutes(1),
                        )
                    ],
                    left_annotations=[
                        cw.HorizontalAnnotation(value=1, label="Alarm threshold (<1)", color=cw.Color.RED),
                    ],
                    width=4, height=5,
                )
            )
        dashboard.add_widgets(*running_task_widgets)

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

        # ALB Metrics — one row per service, since each service has its own ALB.
        # The AWS/ApplicationELB metrics require a LoadBalancer dimension; without
        # it the query resolves to nothing and the widget shows "No data".
        if alb_full_names:
            def _alb_metric(alb: str, name: str, statistic: str, label: str) -> cw.Metric:
                return cw.Metric(
                    namespace="AWS/ApplicationELB",
                    metric_name=name,
                    dimensions_map={"LoadBalancer": alb},
                    statistic=statistic,
                    period=Duration.minutes(1),
                    label=label,
                )

            # Row: request count across every service ALB (one curve per service)
            dashboard.add_widgets(
                cw.GraphWidget(
                    title="ALB Request Count (per service ALB)",
                    left=[_alb_metric(alb, "RequestCount", "Sum", svc) for svc, alb in alb_full_names.items()],
                    width=12, height=6,
                ),
                cw.GraphWidget(
                    title="ALB Target Response Time (per service ALB)",
                    left=[_alb_metric(alb, "TargetResponseTime", "Average", svc) for svc, alb in alb_full_names.items()],
                    width=12, height=6,
                ),
            )

            # Row: per-service 5xx breakdown — Target vs ELB-generated on the same widget
            dashboard.add_widgets(
                cw.GraphWidget(
                    title="ALB Target 5xx (backend errors, per service)",
                    left=[_alb_metric(alb, "HTTPCode_Target_5XX_Count", "Sum", svc) for svc, alb in alb_full_names.items()],
                    width=12, height=6,
                ),
                cw.GraphWidget(
                    title="ALB ELB-generated 5xx (no healthy targets, per service)",
                    left=[_alb_metric(alb, "HTTPCode_ELB_5XX_Count", "Sum", svc) for svc, alb in alb_full_names.items()],
                    left_annotations=[
                        cw.HorizontalAnnotation(value=5, label="Alarm threshold", color=cw.Color.RED),
                    ],
                    width=12, height=6,
                ),
            )

            # ALB target health (Lab 2 signal — targets fall out when SG blocks DB).
            # HealthyHostCount / UnHealthyHostCount are only published when
            # queried with both LoadBalancer AND TargetGroup dimensions.
            def _tg_metric(svc: str, name: str, statistic: str, label: str) -> cw.Metric:
                dims: dict[str, str] = {"LoadBalancer": alb_full_names[svc]}
                if svc in tg_full_names:
                    dims["TargetGroup"] = tg_full_names[svc]
                return cw.Metric(
                    namespace="AWS/ApplicationELB",
                    metric_name=name,
                    dimensions_map=dims,
                    statistic=statistic,
                    period=Duration.minutes(1),
                    label=label,
                )

            dashboard.add_widgets(
                cw.GraphWidget(
                    title="ALB Healthy Hosts (per service target group)",
                    left=[_tg_metric(svc, "HealthyHostCount", "Average", svc) for svc in alb_full_names.keys()],
                    width=12, height=6,
                ),
                cw.GraphWidget(
                    title="ALB Unhealthy Hosts (per service target group)",
                    left=[_tg_metric(svc, "UnHealthyHostCount", "Average", svc) for svc in alb_full_names.keys()],
                    width=12, height=6,
                ),
            )
        else:
            dashboard.add_widgets(
                cw.TextWidget(
                    markdown="_ALB widgets unavailable: MonitoringStack was created without alb_full_names._",
                    width=24, height=3,
                )
            )

        # RDS Metrics
        dashboard.add_widgets(
            cw.GraphWidget(title="RDS CPU", left=[cw.Metric(namespace="AWS/RDS", metric_name="CPUUtilization", statistic="Average", period=Duration.minutes(1))], width=8, height=6),
            cw.GraphWidget(title="RDS Connections", left=[cw.Metric(namespace="AWS/RDS", metric_name="DatabaseConnections", dimensions_map=({"DBInstanceIdentifier": db_instance_identifier} if db_instance_identifier else {}), statistic="Maximum", period=Duration.minutes(1))], width=8, height=6),
            cw.GraphWidget(title="RDS IOPS", left=[cw.Metric(namespace="AWS/RDS", metric_name="ReadIOPS", statistic="Average", period=Duration.minutes(1)), cw.Metric(namespace="AWS/RDS", metric_name="WriteIOPS", statistic="Average", period=Duration.minutes(1))], width=8, height=6),
        )

        # -----------------------------------------------------------------
        # DynamoDB — Lab 3 signals
        # -----------------------------------------------------------------
        # The TransactionAudit table (created by DynamoDBStack) is what
        # scenario 3 throttles. Widgets here are name-referenced so this
        # dashboard does not create a cross-stack dependency on the table
        # construct; the metrics resolve against the fixed table name.
        DDB_TABLE = "PaymentPro-TransactionAudit"
        dashboard.add_widgets(
            cw.GraphWidget(
                title="DynamoDB Throttled Requests (Lab 3)",
                left=[
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="WriteThrottleEvents", dimensions_map={"TableName": DDB_TABLE}, statistic="Sum", period=Duration.minutes(1), label="Write throttles"),
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="ReadThrottleEvents", dimensions_map={"TableName": DDB_TABLE}, statistic="Sum", period=Duration.minutes(1), label="Read throttles"),
                ],
                left_annotations=[
                    cw.HorizontalAnnotation(value=1, label="Alarm threshold (≥1)", color=cw.Color.RED),
                ],
                width=8, height=6,
            ),
            cw.GraphWidget(
                title="DynamoDB Consumed vs Provisioned Capacity",
                left=[
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="ConsumedWriteCapacityUnits", dimensions_map={"TableName": DDB_TABLE}, statistic="Sum", period=Duration.minutes(1), label="Consumed WCU"),
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="ConsumedReadCapacityUnits", dimensions_map={"TableName": DDB_TABLE}, statistic="Sum", period=Duration.minutes(1), label="Consumed RCU"),
                ],
                right=[
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="ProvisionedWriteCapacityUnits", dimensions_map={"TableName": DDB_TABLE}, statistic="Average", period=Duration.minutes(1), label="Provisioned WCU"),
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="ProvisionedReadCapacityUnits", dimensions_map={"TableName": DDB_TABLE}, statistic="Average", period=Duration.minutes(1), label="Provisioned RCU"),
                ],
                width=8, height=6,
            ),
            cw.GraphWidget(
                title="DynamoDB PutItem Latency",
                left=[
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="SuccessfulRequestLatency", dimensions_map={"TableName": DDB_TABLE, "Operation": "PutItem"}, statistic="Average", period=Duration.minutes(1), label="Avg"),
                    cw.Metric(namespace="AWS/DynamoDB", metric_name="SuccessfulRequestLatency", dimensions_map={"TableName": DDB_TABLE, "Operation": "PutItem"}, statistic="p99", period=Duration.minutes(1), label="p99"),
                ],
                width=8, height=6,
            ),
        )

        # =============================================
        # CloudWatch Alarms (all connected to SNS)
        # =============================================

        # ECS CPU Alarms
        for svc in services:
            a = cw.Alarm(self, f"{svc.capitalize()}CpuAlarm", alarm_name=f"PaymentPro-{svc}-HighCPU", alarm_description=f"{svc}-service CPU > 70%", metric=cw.Metric(namespace="AWS/ECS", metric_name="CPUUtilization", dimensions_map={"ClusterName": "payment-processor", "ServiceName": f"{svc}-service"}, statistic="Average", period=Duration.minutes(1)), threshold=70, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING)
            a.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            alarms_by_group["ECS"].append(a)

        # ECS Memory Alarms
        for svc in services:
            a = cw.Alarm(self, f"{svc.capitalize()}MemAlarm", alarm_name=f"PaymentPro-{svc}-HighMemory", alarm_description=f"{svc}-service Memory > 80%", metric=cw.Metric(namespace="AWS/ECS", metric_name="MemoryUtilization", dimensions_map={"ClusterName": "payment-processor", "ServiceName": f"{svc}-service"}, statistic="Average", period=Duration.minutes(1)), threshold=80, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING)
            a.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            alarms_by_group["ECS"].append(a)

        # ECS No Running Tasks Alarms
        for svc in services:
            a = cw.Alarm(self, f"{svc.capitalize()}NoTasksAlarm", alarm_name=f"PaymentPro-{svc}-NoRunningTasks", alarm_description=f"{svc}-service has 0 running tasks", metric=cw.Metric(namespace="ECS/ContainerInsights", metric_name="RunningTaskCount", dimensions_map={"ClusterName": "payment-processor", "ServiceName": f"{svc}-service"}, statistic="Average", period=Duration.minutes(1)), threshold=1, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.LESS_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING)
            a.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            alarms_by_group["ECS"].append(a)

        # ALB Alarms — one alarm per service ALB. Metrics require the
        # LoadBalancer dimension or they resolve to no data and never fire.
        for svc, alb in alb_full_names.items():
            svc_cap = svc.capitalize()
            a5xx = cw.Alarm(
                self, f"Alb5xxAlarm{svc_cap}",
                alarm_name=f"PaymentPro-ALB-{svc}-High5xxErrors",
                alarm_description=f"{svc}-service ALB > 5 ELB-generated 5xx errors/min (typically means no healthy targets)",
                metric=cw.Metric(
                    namespace="AWS/ApplicationELB",
                    metric_name="HTTPCode_ELB_5XX_Count",
                    dimensions_map={"LoadBalancer": alb},
                    statistic="Sum",
                    period=Duration.minutes(1),
                ),
                threshold=5,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            a5xx.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            alarms_by_group["ALB"].append(a5xx)

            alatency = cw.Alarm(
                self, f"AlbLatencyAlarm{svc_cap}",
                alarm_name=f"PaymentPro-ALB-{svc}-HighLatency",
                alarm_description=f"{svc}-service ALB p95 target response time > 1s",
                metric=cw.Metric(
                    namespace="AWS/ApplicationELB",
                    metric_name="TargetResponseTime",
                    dimensions_map={"LoadBalancer": alb},
                    statistic="p95",
                    period=Duration.minutes(1),
                ),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            alatency.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            alarms_by_group["ALB"].append(alatency)

        # RDS Alarms
        rds_cpu = cw.Alarm(self, "RdsCpuAlarm", alarm_name="PaymentPro-RDS-HighCPU", alarm_description="RDS CPU > 70%", metric=cw.Metric(namespace="AWS/RDS", metric_name="CPUUtilization", statistic="Average", period=Duration.minutes(1)), threshold=70, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING)
        rds_cpu.add_alarm_action(cw_actions.SnsAction(alarm_topic))
        alarms_by_group["RDS"].append(rds_cpu)

        rds_conn = cw.Alarm(self, "RdsConnectionsAlarm", alarm_name="PaymentPro-RDS-HighConnections", alarm_description="RDS connections > 30", metric=cw.Metric(namespace="AWS/RDS", metric_name="DatabaseConnections", dimensions_map=({"DBInstanceIdentifier": db_instance_identifier} if db_instance_identifier else {}), statistic="Maximum", period=Duration.minutes(1)), threshold=30, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING)
        rds_conn.add_alarm_action(cw_actions.SnsAction(alarm_topic))
        alarms_by_group["RDS"].append(rds_conn)

        rds_iops = cw.Alarm(self, "RdsIopsAlarm", alarm_name="PaymentPro-RDS-HighIOPS", alarm_description="RDS IOPS > 500", metric=cw.Metric(namespace="AWS/RDS", metric_name="ReadIOPS", statistic="Average", period=Duration.minutes(1)), threshold=500, evaluation_periods=1, comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD, treat_missing_data=cw.TreatMissingData.NOT_BREACHING)
        rds_iops.add_alarm_action(cw_actions.SnsAction(alarm_topic))
        alarms_by_group["RDS"].append(rds_iops)

        # DynamoDB alarms live in PaymentProcessor-DynamoDB (they are created
        # there so they can reference the table's metric_throttled_requests_for_operations
        # helper). Reference them here by name so they show in the roll-up
        # widget below alongside every other alarm. No cross-stack dependency
        # is created — Alarm.from_alarm_name resolves by string.
        for ddb_alarm_name in ("PaymentPro-DynamoDB-WriteThrottled", "PaymentPro-DynamoDB-ReadThrottled"):
            alarms_by_group["DynamoDB"].append(
                cw.Alarm.from_alarm_name(self, ddb_alarm_name.replace("-", ""), ddb_alarm_name)
            )

        # -----------------------------------------------------------------
        # Alarm-status roll-up rows — appended LAST so the alarms lists are
        # fully populated by the time the widget is materialised. CloudWatch
        # ignores dashboard.add_widgets ordering for layout (each widget's
        # x/y is assigned by CDK), but for correctness the alarm list must
        # be non-empty at synth time.
        # -----------------------------------------------------------------
        dashboard.add_widgets(
            cw.AlarmStatusWidget(
                title="ECS Alarms (CPU / Memory / RunningTasks per service)",
                alarms=alarms_by_group["ECS"],
                width=24, height=6,
            ),
        )
        dashboard.add_widgets(
            cw.AlarmStatusWidget(
                title="ALB + RDS + DynamoDB Alarms",
                alarms=alarms_by_group["ALB"] + alarms_by_group["RDS"] + alarms_by_group["DynamoDB"],
                width=24, height=6,
            ),
        )

        # =============================================
        # Outputs
        # =============================================
        CfnOutput(self, "DashboardUrl", value=f"https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=PaymentPro-Operations")
        CfnOutput(self, "SnsTopicArn", value=alarm_topic.topic_arn)
        CfnOutput(self, "WebhookLambdaName", value=webhook_lambda.function_name)
        CfnOutput(self, "AccessLogsBucket", value=access_logs_bucket.bucket_name)
