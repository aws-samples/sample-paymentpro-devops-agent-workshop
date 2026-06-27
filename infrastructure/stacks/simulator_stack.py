"""Lambda + EventBridge stack for automated traffic generation."""

from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    CfnOutput,
)
from constructs import Construct


class SimulatorStack(Stack):
    """Lambda function triggered by EventBridge to generate payment traffic."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        payment_alb_dns: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda function
        traffic_lambda = _lambda.Function(
            self, "TrafficGenerator",
            function_name="payment-traffic-generator",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="traffic_generator.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),
            memory_size=128,
            environment={
                "API_URL": f"http://{payment_alb_dns}",
                "PAYMENT_COUNT": "5",
                "PAYMENT_PROFILE": "mixed",
                "MERCHANT_ID": "demo",
            },
            description="Generates simulated payment traffic every 5 minutes",
        )

        # EventBridge rule — every 5 minutes
        rule = events.Rule(
            self, "TrafficSchedule",
            rule_name="payment-traffic-every-5min",
            schedule=events.Schedule.rate(Duration.minutes(5)),
            description="Triggers payment traffic generator every 5 minutes",
        )
        rule.add_target(targets.LambdaFunction(traffic_lambda))

        # Outputs
        CfnOutput(self, "LambdaFunctionName", value=traffic_lambda.function_name)
        CfnOutput(self, "ScheduleRuleName", value=rule.rule_name)
        CfnOutput(
            self, "DisableCommand",
            value=f"aws events disable-rule --name {rule.rule_name} --profile YOUR_PROFILE",
            description="Run this to stop automatic traffic generation",
        )
        CfnOutput(
            self, "EnableCommand",
            value=f"aws events enable-rule --name {rule.rule_name} --profile YOUR_PROFILE",
            description="Run this to resume automatic traffic generation",
        )
