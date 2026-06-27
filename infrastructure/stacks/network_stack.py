"""VPC and networking infrastructure."""

from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    """VPC with public and private subnets for the payment platform."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self, "PaymentVpc",
            vpc_name="payment-processor-vpc",
            max_azs=2,
            nat_gateways=1,  # Cost optimization for MVP (1 NAT instead of 2)
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )
