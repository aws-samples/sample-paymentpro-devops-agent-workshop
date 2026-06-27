"""RDS PostgreSQL database infrastructure."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Shared PostgreSQL RDS instance for all services."""

    def __init__(
        self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Security group for RDS
        self.db_security_group = ec2.SecurityGroup(
            self, "DbSecurityGroup",
            vpc=vpc,
            description="Security group for Payment Processor RDS",
            allow_all_outbound=False,
        )

        # Allow inbound from private subnets (where ECS tasks run)
        self.db_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from VPC",
        )

        # Database credentials in Secrets Manager
        self.db_secret = secretsmanager.Secret(
            self, "DbSecret",
            secret_name="payment-processor/db-credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=32,
            ),
        )

        # RDS PostgreSQL instance (single instance for MVP — not multi-AZ)
        self.db_instance = rds.DatabaseInstance(
            self, "PaymentDb",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15,
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.db_security_group],
            credentials=rds.Credentials.from_secret(self.db_secret),
            database_name="payment_processor",
            multi_az=False,  # MVP cost optimization
            allocated_storage=20,
            max_allocated_storage=50,
            backup_retention=Duration.days(7),
            deletion_protection=False,  # MVP — easy teardown
            removal_policy=RemovalPolicy.DESTROY,  # MVP — easy teardown
        )

        # Outputs
        CfnOutput(self, "DbEndpoint", value=self.db_instance.db_instance_endpoint_address)
        CfnOutput(self, "DbSecretArn", value=self.db_secret.secret_arn)
