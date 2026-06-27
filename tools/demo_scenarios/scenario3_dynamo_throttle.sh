#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Scenario 3: DynamoDB Throttling — Reduced WCU/RCU
# =============================================================================
# Simulates a cost-optimization change gone wrong: provisioned capacity on the
# TransactionAudit DynamoDB table is reduced from 25 WCU to 1 WCU. When
# payment traffic generates audit writes, DynamoDB throttles the requests.
#
# What DevOps Agent should detect:
#   - DynamoDB WriteThrottleEvents metric spike
#   - CloudTrail: UpdateTable API call reducing ProvisionedThroughput
#   - Correlation: capacity reduction timestamp matches throttle start
#   - Impact: Audit writes failing, payment processing degraded
#   - Root cause: WCU reduced from 25 to 1 (insufficient for traffic)
#
# Usage:
#   ./scenario3_dynamo_throttle.sh inject   # Reduce WCU to 1
#   ./scenario3_dynamo_throttle.sh recover  # Restore WCU to 25
#   ./scenario3_dynamo_throttle.sh traffic  # Generate load to trigger throttling
# =============================================================================


REGION="us-east-1"
TABLE_NAME="PaymentPro-TransactionAudit"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Normal capacity
NORMAL_RCU=25
NORMAL_WCU=25

# Throttled capacity (intentionally too low)
THROTTLED_RCU=1
THROTTLED_WCU=1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

check_table_exists() {
    aws dynamodb describe-table \
        --table-name "$TABLE_NAME" \
 \
        --region "$REGION" \
        --query 'Table.TableStatus' \
        --output text 2>/dev/null || echo "NOT_FOUND"
}

inject() {
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  SCENARIO 3: DynamoDB THROTTLING — Reduced WCU/RCU${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  This simulates a cost-optimization change gone wrong."
    echo "  Provisioned capacity is reduced from 25 WCU to 1 WCU."
    echo "  Under normal traffic load, DynamoDB will throttle write requests."
    echo ""
    echo "  Expected behavior:"
    echo "    1. UpdateTable reduces WCU from 25 → 1"
    echo "    2. Traffic generator writes audit records"
    echo "    3. DynamoDB throttles writes (ProvisionedThroughputExceededException)"
    echo "    4. WriteThrottleEvents alarm fires → DevOps Agent investigates"
    echo "    5. Agent finds CloudTrail: UpdateTable with reduced capacity"
    echo ""

    # Check table exists
    echo "  Step 1: Checking DynamoDB table..."
    STATUS=$(check_table_exists)
    if [ "$STATUS" == "NOT_FOUND" ]; then
        echo -e "  ${RED}✗ Table '$TABLE_NAME' not found.${NC}"
        echo "  Deploy it first: cd infrastructure && cdk deploy PaymentProcessor-DynamoDB"
        exit 1
    fi
    echo -e "  ${GREEN}✓ Table exists (status: $STATUS)${NC}"

    # Get current capacity
    echo ""
    echo "  Step 2: Current provisioned capacity:"
    aws dynamodb describe-table \
        --table-name "$TABLE_NAME" \
 \
        --region "$REGION" \
        --query 'Table.ProvisionedThroughput.{ReadCapacityUnits:ReadCapacityUnits,WriteCapacityUnits:WriteCapacityUnits}' \
        --output json | python3 -c "
import json, sys
cap = json.load(sys.stdin)
print(f'    RCU: {cap[\"ReadCapacityUnits\"]}')
print(f'    WCU: {cap[\"WriteCapacityUnits\"]}')
"

    # Reduce capacity
    echo ""
    echo "  Step 3: Reducing provisioned capacity to WCU=$THROTTLED_WCU, RCU=$THROTTLED_RCU..."
    aws dynamodb update-table \
        --table-name "$TABLE_NAME" \
        --provisioned-throughput "ReadCapacityUnits=$THROTTLED_RCU,WriteCapacityUnits=$THROTTLED_WCU" \
 \
        --region "$REGION" \
        --query 'TableDescription.TableStatus' \
        --output text > /dev/null

    # Also reduce GSI capacity
    echo "  Step 4: Reducing GSI capacity (merchant-index)..."
    aws dynamodb update-table \
        --table-name "$TABLE_NAME" \
        --global-secondary-index-updates "[{\"Update\":{\"IndexName\":\"merchant-index\",\"ProvisionedThroughput\":{\"ReadCapacityUnits\":$THROTTLED_RCU,\"WriteCapacityUnits\":$THROTTLED_WCU}}}]" \
 \
        --region "$REGION" \
        --query 'TableDescription.TableStatus' \
        --output text > /dev/null 2>/dev/null || echo "  (GSI update may need table to be ACTIVE first)"

    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  FAULT INJECTED${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  DynamoDB table '$TABLE_NAME' capacity reduced:"
    echo "    WCU: 25 → $THROTTLED_WCU"
    echo "    RCU: 25 → $THROTTLED_RCU"
    echo ""
    echo "  Next step — generate traffic to trigger throttling:"
    echo "    $0 traffic"
    echo ""
    echo "  Timeline (after traffic starts):"
    echo "    ~10s  — First throttled write requests"
    echo "    ~30s  — WriteThrottleEvents metric visible in CloudWatch"
    echo "    ~60s  — PaymentPro-DynamoDB-WriteThrottled alarm fires"
    echo "    ~90s  — DevOps Agent investigation triggered"
    echo ""
    echo "  Monitor throttling:"
    echo "    aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \\"
    echo "      --metric-name WriteThrottleEvents --dimensions Name=TableName,Value=$TABLE_NAME \\"
    echo "      --start-time \$(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \\"
    echo "      --end-time \$(date -u +%Y-%m-%dT%H:%M:%SZ) \\"
    echo "      --period 60 --statistics Sum"
    echo ""
    echo "  Recover:"
    echo "    $0 recover"
    echo ""
}

traffic() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  GENERATING TRAFFIC → DynamoDB Audit Writes${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Writing 100 audit records rapidly to trigger throttling..."
    echo "  (With WCU=1, any burst >1 write/sec will be throttled)"
    echo ""

    python3 - << 'PYTHON'
import os
import boto3
import json
import uuid
import time
import random
from datetime import datetime

session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'), region_name='us-east-1')
dynamodb = session.resource('dynamodb')
table = dynamodb.Table('PaymentPro-TransactionAudit')

payment_types = ['UPI', 'CREDIT_CARD', 'DEBIT_CARD', 'WALLET']
statuses = ['SUCCESS', 'FAILED', 'PENDING']
merchants = ['merchant-001', 'merchant-002', 'merchant-003', 'merchant-004']

success = 0
throttled = 0
errors = 0

print(f"  Starting burst writes at {datetime.utcnow().strftime('%H:%M:%S')} UTC")
print(f"  {'─' * 50}")

for i in range(100):
    try:
        item = {
            'transaction_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'merchant_id': random.choice(merchants),
            'payment_type': random.choice(payment_types),
            'amount': str(round(random.uniform(10, 10000), 2)),
            'currency': 'INR',
            'status': random.choice(statuses),
            'audit_event': 'PAYMENT_PROCESSED',
            'ttl': int(time.time()) + 86400,  # 24h TTL
        }
        table.put_item(Item=item)
        success += 1
        if (i + 1) % 10 == 0:
            print(f"  Writes: {i+1}/100 | Success: {success} | Throttled: {throttled}")
    except Exception as e:
        if 'ProvisionedThroughputExceededException' in str(type(e).__name__) or 'Throughput' in str(e):
            throttled += 1
            if throttled == 1:
                print(f"  ⚡ First throttle detected at write #{i+1}")
        else:
            errors += 1
            if errors <= 3:
                print(f"  ✗ Error: {e}")

    # Small delay to sustain traffic over time (but still exceed 1 WCU)
    time.sleep(0.05)

print(f"  {'─' * 50}")
print(f"  Results:")
print(f"    Total:     100 writes")
print(f"    Success:   {success}")
print(f"    Throttled: {throttled}")
print(f"    Errors:    {errors}")
print(f"")
if throttled > 0:
    print(f"  ✅ Throttling detected! DynamoDB alarm should fire within 60 seconds.")
else:
    print(f"  ⚠️  No throttling detected. Try running again or check table capacity.")
PYTHON

    echo ""
    echo "  Check alarm status:"
    echo "    aws cloudwatch describe-alarms --alarm-names PaymentPro-DynamoDB-WriteThrottled --query 'MetricAlarms[0].StateValue' --output text"
    echo ""
}

recover() {
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  RECOVERING: Restoring DynamoDB provisioned capacity${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    echo "  Restoring capacity to WCU=$NORMAL_WCU, RCU=$NORMAL_RCU..."
    aws dynamodb update-table \
        --table-name "$TABLE_NAME" \
        --provisioned-throughput "ReadCapacityUnits=$NORMAL_RCU,WriteCapacityUnits=$NORMAL_WCU" \
 \
        --region "$REGION" \
        --query 'TableDescription.TableStatus' \
        --output text > /dev/null

    echo "  Restoring GSI capacity..."
    aws dynamodb update-table \
        --table-name "$TABLE_NAME" \
        --global-secondary-index-updates "[{\"Update\":{\"IndexName\":\"merchant-index\",\"ProvisionedThroughput\":{\"ReadCapacityUnits\":10,\"WriteCapacityUnits\":10}}}]" \
 \
        --region "$REGION" \
        --query 'TableDescription.TableStatus' \
        --output text > /dev/null 2>/dev/null || true

    echo ""
    echo -e "  ${GREEN}✓ Capacity restored.${NC}"
    echo ""
    echo "  New capacity:"
    echo "    WCU: $NORMAL_WCU"
    echo "    RCU: $NORMAL_RCU"
    echo ""
    echo "  DynamoDB capacity changes take effect within seconds."
    echo "  Throttling will stop immediately for new requests."
    echo ""

    # Reset alarms
    echo "  Resetting alarms..."
    python3 "$PROJECT_ROOT/tools/reset_alarms.py"
}

# Main
case "${1:-}" in
    inject)
        inject
        ;;
    traffic)
        traffic
        ;;
    recover)
        recover
        ;;
    *)
        echo "Usage: $0 {inject|traffic|recover}"
        echo ""
        echo "  inject  — Reduce DynamoDB WCU/RCU to 1 (causes throttling under load)"
        echo "  traffic — Generate burst writes to trigger throttling"
        echo "  recover — Restore DynamoDB WCU/RCU to 25"
        exit 1
        ;;
esac
