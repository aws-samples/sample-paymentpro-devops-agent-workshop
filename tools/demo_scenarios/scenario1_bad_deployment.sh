#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Scenario 1: Bad Deployment — Runtime crash (missing module import)
# =============================================================================
# Simulates a bad commit slipping through CI that introduces a missing module
# import. A new task-definition revision is registered with a container
# command that immediately fails on `import nonexistent_payment_module`.
# ECS starts the new task, the container exits, ECS retries → crash loop.
#
# This script does NOT build a container image. It registers a new revision
# of the existing fraud-service task definition with an overridden command,
# so it runs anywhere the AWS CLI is available — including AWS CloudShell.
#
# What DevOps Agent should detect:
#   - Correlation between deployment event (new task definition) and immediate
#     runtime errors (ModuleNotFoundError in CloudWatch Logs)
#   - ECS task stop reason: "Essential container in task exited"
#   - CloudTrail: RegisterTaskDefinition + UpdateService API calls
#   - Impact: All payment validation fails -> 5xx on payment attempts
#
# Usage:
#   ./scenario1_bad_deployment.sh inject   # Roll out broken task definition
#   ./scenario1_bad_deployment.sh recover  # Roll back to good task definition
# =============================================================================

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
CLUSTER="payment-processor"
SERVICE="fraud-service"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# AWS CLI options (use AWS_PROFILE if set, otherwise rely on ambient creds)
AWS_OPTS=("--region" "$REGION")
if [ -n "${AWS_PROFILE:-}" ]; then
    AWS_OPTS+=("--profile" "$AWS_PROFILE")
fi

inject() {
    echo -e "${RED}===============================================================${NC}"
    echo -e "${RED}  SCENARIO 1: BAD DEPLOYMENT - Missing Module Import${NC}"
    echo -e "${RED}===============================================================${NC}"
    echo ""
    echo "  This will register a new task-definition revision for fraud-service"
    echo "  whose container command tries to import a Python module that does"
    echo "  not exist, then deploy that revision."
    echo ""
    echo "  Expected behavior:"
    echo "    1. New task-def revision registered with broken command"
    echo "    2. ECS starts new task, container crashes immediately"
    echo "    3. ECS retries, crash loop (task stops repeatedly)"
    echo "    4. NoRunningTasks alarm fires, DevOps Agent investigates"
    echo ""

    # Save current task definition ARN for rollback
    CURRENT_TASK_DEF=$(aws ecs describe-services \
        --cluster "$CLUSTER" \
        --services "$SERVICE" \
        "${AWS_OPTS[@]}" \
        --query 'services[0].taskDefinition' \
        --output text)
    echo "$CURRENT_TASK_DEF" > /tmp/fraud_good_taskdef.txt
    echo -e "  ${GREEN}* Saved current task def for rollback: $CURRENT_TASK_DEF${NC}"

    # Fetch the current task definition JSON
    aws ecs describe-task-definition \
        --task-definition "$CURRENT_TASK_DEF" \
        "${AWS_OPTS[@]}" \
        --query 'taskDefinition' > /tmp/fraud_taskdef.json

    # Build the broken revision: override the container command to fail on import.
    # The container image and everything else stays the same; only `command` changes.
    python3 - << 'PYTHON'
import json

with open("/tmp/fraud_taskdef.json") as f:
    td = json.load(f)

# Override the command on the first (and only) container.
# This Python one-liner imports a module that doesn't exist, exits non-zero.
td["containerDefinitions"][0]["command"] = [
    "python",
    "-c",
    "import nonexistent_payment_module  # BAD COMMIT: dependency missing",
]

# Remove non-registerable fields
for k in [
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy",
]:
    td.pop(k, None)

with open("/tmp/fraud_taskdef_broken.json", "w") as f:
    json.dump(td, f)
PYTHON

    echo ""
    echo "  Step 1: Registering new task-definition revision with broken command..."

    NEW_REV=$(aws ecs register-task-definition \
        --cli-input-json "file:///tmp/fraud_taskdef_broken.json" \
        "${AWS_OPTS[@]}" \
        --query 'taskDefinition.revision' \
        --output text)
    FAMILY=$(aws ecs describe-task-definition \
        --task-definition "$CURRENT_TASK_DEF" \
        "${AWS_OPTS[@]}" \
        --query 'taskDefinition.family' \
        --output text)

    echo -e "  ${GREEN}* Registered broken task def: ${FAMILY}:${NEW_REV}${NC}"

    echo ""
    echo "  Step 2: Deploying broken revision to ECS (force new deployment)..."
    aws ecs update-service \
        --cluster "$CLUSTER" \
        --service "$SERVICE" \
        --task-definition "${FAMILY}:${NEW_REV}" \
        --force-new-deployment \
        "${AWS_OPTS[@]}" \
        --query 'service.status' \
        --output text > /dev/null

    echo ""
    echo -e "${RED}===============================================================${NC}"
    echo -e "${RED}  FAULT INJECTED${NC}"
    echo -e "${RED}===============================================================${NC}"
    echo ""
    echo "  The fraud-service will now crash on startup with:"
    echo "    ModuleNotFoundError: No module named 'nonexistent_payment_module'"
    echo ""
    echo "  Timeline:"
    echo "    ~30s   ECS starts new task, container crashes"
    echo "    ~60s   ECS retries, crash loop detected"
    echo "    ~90s   Old task drained, NoRunningTasks alarm fires"
    echo "    ~120s  DevOps Agent webhook triggered, investigation begins"
    echo ""
    echo "  Recover:"
    echo "    $0 recover"
    echo ""
}

recover() {
    echo -e "${GREEN}===============================================================${NC}"
    echo -e "${GREEN}  RECOVERING: Rolling back fraud-service${NC}"
    echo -e "${GREEN}===============================================================${NC}"
    echo ""

    if [ -f /tmp/fraud_good_taskdef.txt ]; then
        GOOD_TASK_DEF=$(cat /tmp/fraud_good_taskdef.txt)
        echo "  Rolling back to: $GOOD_TASK_DEF"
    else
        echo -e "${YELLOW}  No saved task def found. Using previous revision...${NC}"
        # Find the last good revision (current - 1)
        CURRENT_TASK_DEF=$(aws ecs describe-services \
            --cluster "$CLUSTER" \
            --services "$SERVICE" \
            "${AWS_OPTS[@]}" \
            --query 'services[0].taskDefinition' \
            --output text)
        FAMILY=$(echo "$CURRENT_TASK_DEF" | cut -d: -f1 | rev | cut -d/ -f1 | rev)
        CURRENT_REV=$(echo "$CURRENT_TASK_DEF" | rev | cut -d: -f1 | rev)
        GOOD_REV=$((CURRENT_REV - 1))
        GOOD_TASK_DEF="${FAMILY}:${GOOD_REV}"
        echo "  Using previous revision: $GOOD_TASK_DEF"
    fi

    aws ecs update-service \
        --cluster "$CLUSTER" \
        --service "$SERVICE" \
        --task-definition "$GOOD_TASK_DEF" \
        --force-new-deployment \
        "${AWS_OPTS[@]}" \
        --query 'service.status' \
        --output text > /dev/null

    echo ""
    echo -e "  ${GREEN}* Rollback initiated. Service will stabilize in ~60 seconds.${NC}"
    echo ""

    # Reset alarms (best-effort)
    if [ -f "$PROJECT_ROOT/tools/reset_alarms.py" ]; then
        echo "  Resetting alarms..."
        python3 "$PROJECT_ROOT/tools/reset_alarms.py" || true
    fi
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
        echo "  inject  - Deploy a broken fraud-service task definition (missing import)"
        echo "  recover - Roll back to the last known good task definition"
        exit 1
        ;;
esac
