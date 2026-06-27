# Infrastructure — AWS CDK Deployment

AWS CDK (Python) infrastructure for deploying the PaymentPro platform to AWS.

## Architecture

```
CloudFront → S3 (Frontend SPA)

ALB (public) → Payment Service (Fargate)
                    ├── Fraud Service (Fargate, internal)
                    ├── Routing Service (Fargate, internal)
                    └── Merchant Service (Fargate, internal)
               Analytics Service (Fargate, internal)

RDS PostgreSQL (isolated subnet, shared by Routing/Merchant/Payment/Analytics)
```

## Stacks

| Stack | Resources |
|-------|-----------|
| `PaymentProcessor-Network` | VPC, 2 AZs, public/private/isolated subnets, NAT Gateway |
| `PaymentProcessor-Database` | RDS PostgreSQL 15 (db.t3.small), Secrets Manager |
| `PaymentProcessor-Services` | ECS Cluster, 5 Fargate services, ALBs, auto-scaling |
| `PaymentProcessor-Frontend` | S3 bucket, CloudFront distribution (HTTPS) |

## Prerequisites

- **AWS CLI** configured with your profile (`aws configure --profile YOUR_PROFILE`)
- **mise** (for Node.js 22 version management) — already on your machine
- **Python 3.12+**
- **Finch** (preferred) or Docker for container image builds
- **Frontend built** (the deploy script handles this automatically)

## Quick Deploy (Recommended)

The `deploy.sh` script handles everything — Node version, Python venv, frontend build, container runtime detection:

```bash
cd infrastructure

# First time only — bootstrap CDK in your AWS account
./deploy.sh YOUR_AWS_PROFILE bootstrap

# Deploy all stacks
./deploy.sh YOUR_AWS_PROFILE
```

That's it. The script will:
1. Detect Finch (preferred) or Docker for container builds
2. Activate mise to use Node 22 (required by CDK)
3. Create/activate a Python venv and install CDK dependencies
4. Build the frontend
5. Run `cdk deploy --all`

## Deploy Script Commands

```bash
./deploy.sh YOUR_AWS_PROFILE              # Deploy all stacks
./deploy.sh YOUR_AWS_PROFILE synth        # Synthesize CloudFormation (no deploy)
./deploy.sh YOUR_AWS_PROFILE diff         # Show pending changes vs deployed
./deploy.sh YOUR_AWS_PROFILE list         # List all stacks
./deploy.sh YOUR_AWS_PROFILE destroy      # Tear down ALL resources
./deploy.sh YOUR_AWS_PROFILE bootstrap    # Bootstrap CDK (first time only)
```

## Manual Setup (If Not Using deploy.sh)

### 1. Install Node 22 via mise

```bash
cd infrastructure
mise install    # Reads .tool-versions, installs Node 22
```

### 2. Python venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Set container runtime

```bash
# Finch (preferred)
export CDK_DOCKER=finch

# Or Docker
export CDK_DOCKER=docker
```

### 4. Build frontend

```bash
cd ../frontend && npm install && npm run build && cd ../infrastructure
```

### 5. Deploy

```bash
cdk bootstrap --profile YOUR_AWS_PROFILE   # First time only
cdk deploy --all --profile YOUR_AWS_PROFILE
```

## Outputs

After deployment, CDK outputs:

| Output | Description |
|--------|-------------|
| `PaymentServiceUrl` | ALB DNS for the Payment API |
| `FrontendUrl` | CloudFront URL for the React app |
| `DbEndpoint` | RDS endpoint (internal, not publicly accessible) |
| `ClusterName` | ECS cluster name |

## Cost Estimate (MVP)

| Resource | Monthly Cost |
|----------|-------------|
| NAT Gateway (1) | ~$32 |
| RDS db.t3.small | ~$25 |
| ECS Fargate (5 services × 0.25 vCPU) | ~$45 |
| ALB (public + internal) | ~$20 |
| CloudFront + S3 | ~$1 |
| **Total** | **~$123/month** |

## Teardown

```bash
./deploy.sh YOUR_AWS_PROFILE destroy
```

All resources are configured with `removal_policy=DESTROY` and `deletion_protection=False` for easy MVP teardown. RDS data will be lost.

## Container Runtime: Finch vs Docker

This project uses **Finch first, Docker as fallback**. The `CDK_DOCKER` environment variable tells CDK which runtime to use for building container images.

The deploy script auto-detects:
```bash
if command -v finch &> /dev/null; then
    export CDK_DOCKER=finch
elif command -v docker &> /dev/null; then
    export CDK_DOCKER=docker
fi
```

## Troubleshooting

### "Cannot find file at .../Dockerfile"
- Ensure you're running from the `infrastructure/` directory
- The Docker build context is the project root (`..`)

### Node version errors / jsii errors
- Run `mise install` in the `infrastructure/` directory to get Node 22
- Or use the deploy script which handles this automatically

### "No credentials" error
- Verify your AWS profile: `aws sts get-caller-identity --profile YOUR_PROFILE`
- Ensure the profile has sufficient permissions (Admin or PowerUser)

### Finch not building images
- Ensure Finch VM is running: `finch vm start`
- Check: `finch --version`
