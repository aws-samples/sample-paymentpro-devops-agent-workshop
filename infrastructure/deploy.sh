#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Payment Processor — AWS CDK Deployment Script
# ============================================================
# Usage:
#   ./deploy.sh <AWS_PROFILE> [COMMAND]
#
# Examples:
#   ./deploy.sh my-profile          # Deploy all stacks
#   ./deploy.sh my-profile synth    # Synthesize only (no deploy)
#   ./deploy.sh my-profile diff     # Show changes
#   ./deploy.sh my-profile destroy  # Tear down all resources
#   ./deploy.sh my-profile list     # List stacks
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Validate arguments ---
if [ $# -lt 1 ]; then
    echo "Usage: ./deploy.sh <AWS_PROFILE> [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  (none)    Deploy all stacks"
    echo "  synth     Synthesize CloudFormation templates"
    echo "  diff      Show pending changes"
    echo "  destroy   Tear down all resources"
    echo "  list      List all stacks"
    echo "  bootstrap Bootstrap CDK (first time only)"
    exit 1
fi

AWS_PROFILE="$1"
COMMAND="${2:-deploy}"

echo "=== Payment Processor CDK Deployment ==="
echo "Profile: $AWS_PROFILE"
echo "Command: $COMMAND"
echo ""

# --- Detect container runtime (Finch first, then Docker) ---
if command -v finch &> /dev/null; then
    export CDK_DOCKER=finch
    echo "✓ Container runtime: finch"
elif command -v docker &> /dev/null; then
    export CDK_DOCKER=docker
    echo "✓ Container runtime: docker"
else
    echo "✗ ERROR: Neither finch nor docker found. Please install one."
    exit 1
fi

# --- Ensure Node 22 via mise ---
if command -v mise &> /dev/null; then
    echo "✓ Using mise for Node.js version management"
    eval "$(mise activate bash)"
    mise install --yes 2>/dev/null || true
    NODE_VERSION=$(node --version)
    echo "✓ Node.js: $NODE_VERSION"
else
    NODE_VERSION=$(node --version 2>/dev/null || echo "not found")
    echo "⚠ mise not found. Using system Node.js: $NODE_VERSION"
    echo "  If CDK fails, install mise and run: mise install"
fi

# --- Setup Python venv ---
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "→ Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
echo "✓ Python venv: $VENV_DIR"

# --- Install CDK dependencies ---
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "✓ CDK dependencies installed"

# --- Install CDK CLI if not available ---
if ! command -v cdk &> /dev/null; then
    echo "→ Installing AWS CDK CLI..."
    npm install -g aws-cdk
fi
echo "✓ CDK CLI: $(cdk --version)"

# --- Build frontend (needed for FrontendStack) ---
if [ "$COMMAND" = "deploy" ] || [ "$COMMAND" = "synth" ]; then
    echo ""
    echo "→ Building frontend..."
    cd "$PROJECT_ROOT/frontend"
    npm install --silent
    npm run build
    echo "✓ Frontend built"
    cd "$SCRIPT_DIR"
fi

# --- Silence jsii Node version warning ---
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

# --- Execute CDK command ---
echo ""
echo "→ Running: cdk $COMMAND --all --profile $AWS_PROFILE"
echo ""

case "$COMMAND" in
    deploy)
        cdk deploy --all --profile "$AWS_PROFILE" --require-approval broadening
        ;;
    synth)
        cdk synth --profile "$AWS_PROFILE"
        ;;
    diff)
        cdk diff --all --profile "$AWS_PROFILE"
        ;;
    destroy)
        echo "⚠ This will DESTROY all resources. Are you sure? (Ctrl+C to cancel)"
        cdk destroy --all --profile "$AWS_PROFILE"
        ;;
    list)
        cdk list --profile "$AWS_PROFILE"
        ;;
    bootstrap)
        cdk bootstrap --profile "$AWS_PROFILE"
        ;;
    *)
        echo "Unknown command: $COMMAND"
        exit 1
        ;;
esac

echo ""
echo "=== Done ==="
