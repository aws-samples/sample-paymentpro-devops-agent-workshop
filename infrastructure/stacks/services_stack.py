"""ECS Fargate services infrastructure — all 5 backend microservices."""

import os

from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
    Fn,
)
from constructs import Construct

from stacks.database_stack import DatabaseStack


# When USE_PREBUILT_IMAGES is "true", the CDK consumes images from ECR
# (built+pushed by the GitLab CI pipeline). When unset/false (the default),
# CDK builds from each service's Dockerfile via `from_asset` — which is what
# `./deploy.sh` and the workshop's CodeBuild path do.
USE_PREBUILT_IMAGES = os.environ.get("USE_PREBUILT_IMAGES", "").lower() == "true"
IMAGE_TAG = os.environ.get("IMAGE_TAG", "latest")


class ServicesStack(Stack):
    """ECS Fargate cluster with all backend microservices."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        database: DatabaseStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECS Cluster
        cluster = ecs.Cluster(
            self, "PaymentCluster",
            cluster_name="payment-processor",
            vpc=vpc,
            container_insights=True,
        )

        # Service secret for inter-service auth
        service_secret = secretsmanager.Secret(
            self, "ServiceSecret",
            secret_name="payment-processor/service-secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                password_length=48,
            ),
        )

        # Shared environment variables for all services
        db_endpoint = database.db_instance.db_instance_endpoint_address
        db_port = database.db_instance.db_instance_endpoint_port

        # Common DB env vars (password passed as ECS secret)
        db_env = {
            "DB_HOST": db_endpoint,
            "DB_PORT": db_port,
            "DB_NAME": "payment_processor",
            "DB_USERNAME": "postgres",
        }
        db_secrets = {
            "DB_PASSWORD": ecs.Secret.from_secrets_manager(database.db_secret, field="password"),
        }

        # --- Fraud Service (stateless, no DB) ---
        fraud_service = self._create_service(
            cluster=cluster,
            name="fraud",
            port=8004,
            dockerfile_path="services/fraud/Dockerfile",
            build_context="..",
            environment={
                "ENVIRONMENT": "production",
                "PORT": "8004",
                "METRICS_ENABLED": "true",
                "METRICS_NAMESPACE": "PaymentProcessor/FraudService",
            },
            secrets={
                "SERVICE_SECRET": ecs.Secret.from_secrets_manager(service_secret),
            },
            cpu=256,
            memory=512,
        )

        # --- Routing Service (with DB) ---
        routing_service = self._create_service(
            cluster=cluster,
            name="routing",
            port=8003,
            dockerfile_path="services/routing/Dockerfile",
            build_context="..",
            environment={
                "ENVIRONMENT": "production",
                "PORT": "8003",
                **db_env,
            },
            secrets={
                "SERVICE_SECRET": ecs.Secret.from_secrets_manager(service_secret),
                **db_secrets,
            },
            cpu=256,
            memory=512,
        )

        # --- Merchant Service (with DB) ---
        merchant_service = self._create_service(
            cluster=cluster,
            name="merchant",
            port=8002,
            dockerfile_path="services/merchant/Dockerfile",
            build_context="..",
            environment={
                "ENVIRONMENT": "production",
                "PORT": "8002",
                **db_env,
            },
            secrets={
                "SERVICE_SECRET": ecs.Secret.from_secrets_manager(service_secret),
                **db_secrets,
            },
            cpu=256,
            memory=512,
        )

        # --- Analytics Service (read-only DB access) ---
        analytics_service = self._create_service(
            cluster=cluster,
            name="analytics",
            port=8005,
            dockerfile_path="services/analytics/Dockerfile",
            build_context="..",
            environment={
                "ENVIRONMENT": "production",
                "PORT": "8005",
                **db_env,
            },
            secrets={
                "SERVICE_SECRET": ecs.Secret.from_secrets_manager(service_secret),
                **db_secrets,
            },
            cpu=256,
            memory=512,
        )

        # --- Payment Service (orchestrator, with DB) ---
        fraud_alb = fraud_service.load_balancer.load_balancer_dns_name
        routing_alb = routing_service.load_balancer.load_balancer_dns_name
        merchant_alb = merchant_service.load_balancer.load_balancer_dns_name
        analytics_alb = analytics_service.load_balancer.load_balancer_dns_name

        payment_service = self._create_service(
            cluster=cluster,
            name="payment",
            port=8001,
            dockerfile_path="services/payment/Dockerfile",
            build_context="..",
            environment={
                "ENVIRONMENT": "production",
                "PORT": "8001",
                **db_env,
                "FRAUD_SERVICE_URL": Fn.join("", ["http://", fraud_alb]),
                "ROUTING_SERVICE_URL": Fn.join("", ["http://", routing_alb]),
                "MERCHANT_SERVICE_URL": Fn.join("", ["http://", merchant_alb]),
                "ANALYTICS_SERVICE_URL": Fn.join("", ["http://", analytics_alb]),
            },
            secrets={
                "SERVICE_SECRET": ecs.Secret.from_secrets_manager(service_secret),
                **db_secrets,
            },
            cpu=512,
            memory=1024,
            public=True,  # Payment service is the API entry point
        )

        # Grant DB access
        database.db_secret.grant_read(routing_service.task_definition.task_role)
        database.db_secret.grant_read(merchant_service.task_definition.task_role)
        database.db_secret.grant_read(payment_service.task_definition.task_role)
        database.db_secret.grant_read(analytics_service.task_definition.task_role)

        # Outputs
        self.payment_alb_dns = payment_service.load_balancer.load_balancer_dns_name
        CfnOutput(self, "PaymentServiceUrl", value=self.payment_alb_dns)
        CfnOutput(self, "ClusterName", value=cluster.cluster_name)

    def _create_service(
        self,
        cluster: ecs.Cluster,
        name: str,
        port: int,
        dockerfile_path: str,
        build_context: str,
        environment: dict,
        secrets: dict,
        cpu: int = 256,
        memory: int = 512,
        public: bool = False,
    ) -> ecs_patterns.ApplicationLoadBalancedFargateService:
        """Create a Fargate service with ALB.

        Image source depends on the USE_PREBUILT_IMAGES env var:
        - true  → consume from ECR repo `payment-processor/<name>:<IMAGE_TAG>`
                  (used by the GitLab CI pipeline, no Docker build at synth)
        - false → build the Dockerfile via `from_asset`
                  (used by `./deploy.sh` locally and the workshop's CodeBuild)
        """
        if USE_PREBUILT_IMAGES:
            repo = ecr.Repository.from_repository_name(
                self, f"{name.capitalize()}EcrRepo",
                repository_name=f"payment-processor/{name}",
            )
            container_image = ecs.ContainerImage.from_ecr_repository(repo, IMAGE_TAG)
        else:
            container_image = ecs.ContainerImage.from_asset(
                directory=build_context,
                file=dockerfile_path,
                platform=ecr_assets.Platform.LINUX_AMD64,
                exclude=[
                    "infrastructure",
                    "cdk.out",
                    "frontend/node_modules",
                    "frontend/dist",
                    ".git",
                    "**/__pycache__",
                    "**/.pytest_cache",
                    "**/node_modules",
                    "aidlc-docs",
                    ".kiro",
                ],
            )

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, f"{name.capitalize()}Service",
            cluster=cluster,
            service_name=f"{name}-service",
            cpu=cpu,
            memory_limit_mib=memory,
            desired_count=1,  # MVP — single instance
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=container_image,
                container_port=port,
                environment=environment,
                secrets=secrets,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix=name,
                    log_retention=logs.RetentionDays.ONE_WEEK,
                ),
            ),
            public_load_balancer=public,
            assign_public_ip=False,
            health_check_grace_period=Duration.seconds(60),
        )

        # Configure health check
        service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
        )

        # Auto-scaling (fixed at 1 task — no scaling)
        scaling = service.service.auto_scale_task_count(min_capacity=1, max_capacity=1)

        return service
