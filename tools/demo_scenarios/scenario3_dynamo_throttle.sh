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
    echo -e "${CYAN}  GENERATING TRAFFIC → DynamoDB Audit Writes (5 minutes)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Writing continuously for 5 minutes to exhaust DynamoDB burst credits"
    echo "  and trigger throttling. (DynamoDB accumulates burst capacity from"
    echo "  unused WCU — this sustained load will deplete it.)"
    echo ""
    echo "  Press Ctrl+C to stop early once throttling is detected."
    echo ""

    python3 - << 'PYTHON'
import os
import boto3
import uuid
import time
import random
from datetime import datetime, timezone

session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'), region_name='us-east-1')
# Disable automatic retries so throttle exceptions surface immediately
# instead of the SDK silently retrying with backoff
from botocore.config import Config
no_retry_config = Config(retries={'max_attempts': 0})
dynamodb = session.resource('dynamodb', config=no_retry_config)
table = dynamodb.Table('PaymentPro-TransactionAudit')

payment_types = ['UPI', 'CREDIT_CARD', 'DEBIT_CARD', 'WALLET']
statuses = ['SUCCESS', 'FAILED', 'PENDING']
merchants = ['merchant-001', 'merchant-002', 'merchant-003', 'merchant-004']

success = 0
throttled = 0
errors = 0
duration_seconds = 300  # 5 minutes

start_time = time.time()
print(f"  Started at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC — running for 5 minutes")
print(f"  {'─' * 55}")

try:
    i = 0
    while time.time() - start_time < duration_seconds:
        try:
            table.put_item(Item={
                'transaction_id': str(uuid.uuid4()),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'merchant_id': random.choice(merchants),
                'payment_type': random.choice(payment_types),
                'amount': str(round(random.uniform(10, 10000), 2)),
                'currency': 'INR',
                'status': random.choice(statuses),
                'audit_event': 'PAYMENT_PROCESSED',
                'ttl': int(time.time()) + 86400,
            })
            success += 1
        except Exception as e:
            if 'Throughput' in str(e) or 'Throttl' in str(e):
                throttled += 1
                if throttled == 1:
                    elapsed = int(time.time() - start_time)
                    print(f"  ⚡ First throttle detected after {elapsed}s (write #{i+1})")
            else:
                errors += 1

        i += 1
        # Print status every 30 seconds
        elapsed = time.time() - start_time
        if i % 100 == 0:
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            remaining = duration_seconds - int(elapsed)
            print(f"  [{mins:02d}:{secs:02d}] Writes: {i} | Success: {success} | Throttled: {throttled} | Remaining: {remaining}s")

        # No delay — write as fast as possible to exhaust burst credits
except KeyboardInterrupt:
    print(f"\n  Stopped by user.")

print(f"  {'─' * 55}")
elapsed = int(time.time() - start_time)
print(f"  Results ({elapsed}s elapsed):")
print(f"    Total writes: {i}")
print(f"    Success:      {success}")
print(f"    Throttled:    {throttled}")
print(f"    Errors:       {errors}")
print(f"")
if throttled > 0:
    print(f"  ✅ Throttling detected! DynamoDB alarm should fire within 60 seconds.")
else:
    # Check if writes slowed down significantly (SDK auto-retries hide throttling)
    writes_per_sec = i / max(elapsed, 1)
    if writes_per_sec < 3 and elapsed > 60:
        print(f"  ✅ Write throughput dropped to {writes_per_sec:.1f}/sec (SDK retrying throttled requests).")
        print(f"     DynamoDB alarm should already be firing — the SDK hides throttling via retries.")
    else:
        print(f"  ⚠️  No throttling detected yet. Burst credits may still be draining.")
        print(f"     Run 'traffic' again — throttling typically starts after 2-3 minutes.")
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
    # Check current capacity first so recover is idempotent: DynamoDB rejects an
    # update-table that does not change the throughput with a ValidationException,
    # which would abort the script under 'set -e' if capacity is already restored.
    CURRENT_WCU=$(aws dynamodb describe-table \
        --table-name "$TABLE_NAME" \
        --region "$REGION" \
        --query 'Table.ProvisionedThroughput.WriteCapacityUnits' \
        --output text 2>/dev/null || echo "0")
    if [ "$CURRENT_WCU" == "$NORMAL_WCU" ]; then
        echo "  (Table already at WCU=$NORMAL_WCU — nothing to restore.)"
    else
        aws dynamodb update-table \
            --table-name "$TABLE_NAME" \
            --provisioned-throughput "ReadCapacityUnits=$NORMAL_RCU,WriteCapacityUnits=$NORMAL_WCU" \
 \
            --region "$REGION" \
            --query 'TableDescription.TableStatus' \
            --output text > /dev/null
    fi

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
