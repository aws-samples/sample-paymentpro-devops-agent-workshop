#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Scenario 2: Security Group Removal — App → Database connectivity severed
# =============================================================================
# Simulates an accidental security-group change (e.g., cost-optimization
# script, Terraform drift, or manual console change) that removes the
# ingress rule allowing ECS services to connect to RDS PostgreSQL on port 5432.
#
# What DevOps Agent should detect:
#   - Sudden spike in 5xx errors from all DB-dependent services
#   - Connection timeout patterns in service logs
#   - CloudTrail: RevokeSecurityGroupIngress API call
#   - Correlation: SG change timestamp matches start of errors
#   - Impact: payment, routing, merchant, analytics all affected (fraud is OK)
#
# Usage:
#   ./scenario2_remove_sg_rule.sh inject   # Remove the DB ingress rule
#   ./scenario2_remove_sg_rule.sh recover  # Restore the DB ingress rule
# =============================================================================


REGION="us-east-1"
CLUSTER="payment-processor"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find the RDS security group
find_rds_sg() {
    # Look for the security group with "DbSecurityGroup" in the description or name
    local sg_id
    sg_id=$(aws ec2 describe-security-groups \
 \
        --region "$REGION" \
        --filters "Name=description,Values=*Payment Processor RDS*" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null)

    if [ "$sg_id" == "None" ] || [ -z "$sg_id" ]; then
        # Try by tag
        sg_id=$(aws ec2 describe-security-groups \
 \
            --region "$REGION" \
            --filters "Name=tag:aws:cloudformation:logical-id,Values=DbSecurityGroup*" \
            --query 'SecurityGroups[0].GroupId' \
            --output text 2>/dev/null)
    fi

    if [ "$sg_id" == "None" ] || [ -z "$sg_id" ]; then
        echo ""
        return 1
    fi
    echo "$sg_id"
}

# Find the VPC CIDR for the payment-processor VPC
find_vpc_cidr() {
    local vpc_cidr
    vpc_cidr=$(aws ec2 describe-vpcs \
 \
        --region "$REGION" \
        --filters "Name=tag:Name,Values=*payment-processor*" \
        --query 'Vpcs[0].CidrBlock' \
        --output text 2>/dev/null)

    if [ "$vpc_cidr" == "None" ] || [ -z "$vpc_cidr" ]; then
        # Fallback: look by CDK stack tag
        vpc_cidr=$(aws ec2 describe-vpcs \
 \
            --region "$REGION" \
            --filters "Name=tag:Project,Values=PaymentPro" \
            --query 'Vpcs[0].CidrBlock' \
            --output text 2>/dev/null)
    fi

    echo "$vpc_cidr"
}

inject() {
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  SCENARIO 2: SECURITY GROUP REMOVAL — DB Connectivity Severed${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  This will remove the ingress rule on the RDS security group that"
    echo "  allows ECS services (VPC CIDR) to connect on port 5432."
    echo ""
    echo "  Expected behavior:"
    echo "    1. All DB-dependent services lose connectivity to PostgreSQL"
    echo "    2. New requests timeout on DB connection (5-30 second delay)"
    echo "    3. ALB health checks fail → services marked unhealthy"
    echo "    4. 5xx errors spike → ALB-High5xxErrors alarm fires"
    echo "    5. DevOps Agent investigates, finds RevokeSecurityGroupIngress in CloudTrail"
    echo ""

    # Find the RDS security group
    echo "  Step 1: Finding RDS security group..."
    SG_ID=$(find_rds_sg)
    if [ -z "$SG_ID" ]; then
        echo -e "  ${RED}✗ Could not find RDS security group. Check that the stack is deployed.${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓ Found RDS SG: $SG_ID${NC}"

    # Find VPC CIDR
    VPC_CIDR=$(find_vpc_cidr)
    if [ -z "$VPC_CIDR" ] || [ "$VPC_CIDR" == "None" ]; then
        echo -e "  ${YELLOW}⚠ Could not determine VPC CIDR. Using default 10.0.0.0/16${NC}"
        VPC_CIDR="10.0.0.0/16"
    fi
    echo -e "  ${GREEN}✓ VPC CIDR: $VPC_CIDR${NC}"

    # Save SG info for recovery
    echo "$SG_ID" > /tmp/rds_sg_id.txt
    echo "$VPC_CIDR" > /tmp/rds_vpc_cidr.txt

    # Check current rules
    echo ""
    echo "  Step 2: Current ingress rules on $SG_ID:"
    aws ec2 describe-security-groups \
        --group-ids "$SG_ID" \
 \
        --query 'SecurityGroups[0].IpPermissions' \
        --output json | python3 -c "
import json, sys
rules = json.load(sys.stdin)
for r in rules:
    port = r.get('FromPort', 'all')
    for cidr in r.get('IpRanges', []):
        print(f'    Port {port}: {cidr[\"CidrIp\"]} ({cidr.get(\"Description\", \"\")})')
"

    # Remove the ingress rule
    echo ""
    echo "  Step 3: Removing PostgreSQL ingress rule (port 5432 from $VPC_CIDR)..."
    aws ec2 revoke-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 5432 \
        --cidr "$VPC_CIDR" \
 \
        --region "$REGION"

    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  FAULT INJECTED${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  The RDS security group no longer allows inbound traffic from the VPC."
    echo "  Existing connections will timeout on next query."
    echo ""
    echo "  Affected services:"
    echo "    ✗ payment-service   (orchestrator — DB writes)"
    echo "    ✗ routing-service   (rule engine — DB reads)"
    echo "    ✗ merchant-service  (auth — DB reads/writes)"
    echo "    ✗ analytics-service (metrics — DB reads)"
    echo "    ✓ fraud-service     (stateless — NO database dependency)"
    echo ""
    echo "  Timeline:"
    echo "    ~10s   — Existing DB connections timeout on next query"
    echo "    ~30s   — Health checks start failing (DB connection error)"
    echo "    ~60s   — ALB marks targets unhealthy"
    echo "    ~90s   — ALB-High5xxErrors alarm fires"
    echo "    ~120s  — DevOps Agent investigation triggered"
    echo ""
    echo "  Generate traffic to accelerate failure detection:"
    echo "    python3 $PROJECT_ROOT/tools/traffic_simulator.py --count 10 --interval 1 -v"
    echo ""
    echo "  Monitor:"
    echo "    aws logs tail /ecs/payment --follow"
    echo ""
    echo "  Recover:"
    echo "    $0 recover"
    echo ""
}

recover() {
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  RECOVERING: Restoring RDS security group ingress rule${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Get saved SG info
    if [ -f /tmp/rds_sg_id.txt ]; then
        SG_ID=$(cat /tmp/rds_sg_id.txt)
        VPC_CIDR=$(cat /tmp/rds_vpc_cidr.txt)
    else
        echo "  No saved SG info. Detecting..."
        SG_ID=$(find_rds_sg)
        VPC_CIDR=$(find_vpc_cidr)
        if [ -z "$VPC_CIDR" ] || [ "$VPC_CIDR" == "None" ]; then
            VPC_CIDR="10.0.0.0/16"
        fi
    fi

    echo "  SG: $SG_ID"
    echo "  CIDR: $VPC_CIDR"
    echo ""
    echo "  Restoring ingress rule (port 5432 from $VPC_CIDR)..."

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 5432 \
        --cidr "$VPC_CIDR" \
 \
        --region "$REGION" 2>/dev/null || echo "  (Rule may already exist)"

    echo ""
    echo -e "  ${GREEN}✓ Ingress rule restored.${NC}"
    echo ""
    echo "  Services will recover automatically as DB connections re-establish."
    echo "  Existing tasks do NOT need restart — they will reconnect."
    echo ""
    echo "  Timeline:"
    echo "    ~10s — New DB connections succeed"
    echo "    ~30s — Health checks pass"
    echo "    ~60s — ALB marks targets healthy"
    echo ""

    # Force new connections by sending traffic
    echo "  Sending traffic to force connection re-establishment..."
    python3 "$PROJECT_ROOT/tools/traffic_simulator.py" --count 5 --interval 1 -v 2>/dev/null || true

    # Reset alarms
    echo ""
    echo "  Resetting alarms..."
    python3 "$PROJECT_ROOT/tools/reset_alarms.py"
}

# Main
case "${1:-}" in
    inject)
        inject
        ;;
    recover)
        recover
        ;;
    *)
        echo "Usage: $0 {inject|recover}"
        echo ""
        echo "  inject  — Remove RDS security group ingress rule (break DB connectivity)"
        echo "  recover — Restore RDS security group ingress rule"
        exit 1
        ;;
esac
