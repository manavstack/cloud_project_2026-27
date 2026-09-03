#!/usr/bin/env bash
# deploy.sh — Build and deploy the Federated Campus Energy Cloud stack
# Usage: bash infrastructure/deploy.sh [STACK_NAME] [REGION]
#
# Prerequisites:
#   pip install aws-sam-cli
#   aws configure   (or set AWS_PROFILE / AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)

set -euo pipefail

STACK_NAME="${1:-campus-energy-cloud}"
REGION="${2:-ap-south-1}"
SAM_S3_BUCKET="${STACK_NAME}-sam-artifacts-${REGION}"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Federated Campus Energy Cloud — Deploy"
echo "  Stack : ${STACK_NAME}"
echo "  Region: ${REGION}"
echo "═══════════════════════════════════════════════════"
echo ""

# ── 1. Ensure SAM artifact bucket exists ────────────────────────────────────
if ! aws s3api head-bucket --bucket "${SAM_S3_BUCKET}" 2>/dev/null; then
  echo "Creating SAM artifact bucket: ${SAM_S3_BUCKET}"
  aws s3 mb "s3://${SAM_S3_BUCKET}" --region "${REGION}"
  aws s3api put-bucket-versioning \
    --bucket "${SAM_S3_BUCKET}" \
    --versioning-configuration Status=Enabled
fi

# ── 2. SAM build ─────────────────────────────────────────────────────────────
echo "Building Lambda packages..."
sam build \
  --template-file infrastructure/template.yaml \
  --build-dir .aws-sam/build \
  --region "${REGION}"

# ── 3. SAM deploy ────────────────────────────────────────────────────────────
echo "Deploying stack: ${STACK_NAME}..."
sam deploy \
  --template-file .aws-sam/build/template.yaml \
  --stack-name "${STACK_NAME}" \
  --s3-bucket "${SAM_S3_BUCKET}" \
  --region "${REGION}" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides StageName=prod \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

# ── 4. Print outputs ─────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo "  Stack deployed. Copy these values into:"
echo "  src/frontend/aws-config.js"
echo "═══════════════════════════════════════════════════"
echo ""

aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table

# ── 5. Seed DynamoDB tables ───────────────────────────────────────────────────
echo ""
read -r -p "Seed DynamoDB tables with initial data? [Y/n] " SEED
if [[ "${SEED}" != "n" && "${SEED}" != "N" ]]; then
  AWS_REGION="${REGION}" python3 src/backend/seed/seed_dynamodb.py
fi

echo ""
echo "Done! Run the dashboard locally with:"
echo "  python3 -m http.server 8000"
echo "  open http://localhost:8000/src/frontend/"
echo ""
