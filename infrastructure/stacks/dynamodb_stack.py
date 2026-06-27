"""DynamoDB table for transaction audit logs — used for DevOps Agent demo."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    Duration,
    CfnOutput,
)
from constructs import Construct


class DynamoDBStack(Stack):
    """DynamoDB table for transaction audit trail.

    This table stores an audit log of every payment transaction for compliance.
    It uses provisioned capacity (not on-demand) to enable the DynamoDB
    throttling demo scenario — reducing WCU/RCU causes write throttling
    during peak transaction windows.

    Demo Scenario 3: Reduce WCU from 25 to 1 → writes throttle under load.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        alarm_topic_arn: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # =============================================
        # DynamoDB Table — Transaction Audit Log
        # =============================================
        self.audit_table = dynamodb.Table(
            self, "TransactionAuditTable",
            table_name="PaymentPro-TransactionAudit",
            partition_key=dynamodb.Attribute(
                name="transaction_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=25,
            write_capacity=25,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,  # Demo table — not needed
            time_to_live_attribute="ttl",
        )

        # GSI for merchant-based queries
        self.audit_table.add_global_secondary_index(
            index_name="merchant-index",
            partition_key=dynamodb.Attribute(
                name="merchant_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING,
            ),
            read_capacity=10,
            write_capacity=10,
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # =============================================
        # CloudWatch Alarms for DynamoDB
        # =============================================

        # Import SNS topic if ARN provided
        alarm_topic = None
        if alarm_topic_arn:
            alarm_topic = sns.Topic.from_topic_arn(
                self, "ImportedAlarmTopic", alarm_topic_arn
            )

        # Write Throttle Alarm
        write_throttle_alarm = cw.Alarm(
            self, "WriteThrottleAlarm",
            alarm_name="PaymentPro-DynamoDB-WriteThrottled",
            alarm_description="DynamoDB TransactionAudit table write requests are being throttled",
            metric=self.audit_table.metric_throttled_requests_for_operations(
                operations=[dynamodb.Operation.PUT_ITEM],
                period=Duration.minutes(1),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # Read Throttle Alarm
        read_throttle_alarm = cw.Alarm(
            self, "ReadThrottleAlarm",
            alarm_name="PaymentPro-DynamoDB-ReadThrottled",
            alarm_description="DynamoDB TransactionAudit table read requests are being throttled",
            metric=self.audit_table.metric_throttled_requests_for_operations(
                operations=[dynamodb.Operation.GET_ITEM, dynamodb.Operation.QUERY],
                period=Duration.minutes(1),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # Connect alarms to SNS if available
        if alarm_topic:
            write_throttle_alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            read_throttle_alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # =============================================
        # Outputs
        # =============================================
        CfnOutput(self, "AuditTableName", value=self.audit_table.table_name)
        CfnOutput(self, "AuditTableArn", value=self.audit_table.table_arn)
