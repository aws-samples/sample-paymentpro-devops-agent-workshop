"""S3 + CloudFront infrastructure for the React frontend with API proxy."""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_deployment as s3_deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
)
from constructs import Construct


class FrontendStack(Stack):
    """S3 bucket + CloudFront distribution for the React SPA.

    CloudFront serves:
    - /* → S3 (frontend static assets)
    - /api/* → Payment Service ALB (backend API proxy)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        payment_alb_dns: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for static assets
        bucket = s3.Bucket(
            self, "FrontendBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # S3 origin for static assets
        s3_origin = origins.S3BucketOrigin.with_origin_access_identity(bucket)

        # Build behaviors list
        additional_behaviors: dict[str, cloudfront.BehaviorOptions] = {}

        # If ALB DNS is provided, add /api/* behavior pointing to ALB
        if payment_alb_dns:
            alb_origin = origins.HttpOrigin(
                payment_alb_dns,
                protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
            )
            additional_behaviors["/api/*"] = cloudfront.BehaviorOptions(
                origin=alb_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            )

        # CloudFront distribution
        distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors=additional_behaviors,
            default_root_object="index.html",
            # SPA routing — return index.html for all 404s (only for S3 origin)
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # Deploy frontend build to S3
        s3_deploy.BucketDeployment(
            self, "DeployFrontend",
            sources=[s3_deploy.Source.asset("../frontend/dist")],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # Outputs
        CfnOutput(self, "FrontendUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=distribution.distribution_id)
