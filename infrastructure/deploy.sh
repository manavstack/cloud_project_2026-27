#!/usr/bin/env bash
# One-command deploy of the Smart Campus Energy Cloud (AWS SAM).
#
#   ./deploy.sh              build + deploy + seed buildings and tariff windows
#   ./deploy.sh outputs      print stack outputs
#   ./deploy.sh destroy      empty the raw bucket and delete the stack
#
# Configure with environment variables (all optional):
#   STACK_NAME (default smart-campus-energy-dev)   AWS_REGION (default ap-south-1)
#   ALERT_EMAIL    PEAK_THRESHOLD_KW (50)    TIMEZONE (Asia/Kolkata)
#   CORS_ORIGIN (http://localhost:3000)      SAGEMAKER_ENDPOINT ("")
#   PROJECT_NAME (smart-campus-energy)       ENVIRONMENT (dev)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

PROJECT_NAME="${PROJECT_NAME:-smart-campus-energy}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${STACK_NAME:-${PROJECT_NAME}-${ENVIRONMENT}}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-south-1}}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
PEAK_THRESHOLD_KW="${PEAK_THRESHOLD_KW:-50}"
TIMEZONE="${TIMEZONE:-Asia/Kolkata}"
CORS_ORIGIN="${CORS_ORIGIN:-http://localhost:3000}"
SAGEMAKER_ENDPOINT="${SAGEMAKER_ENDPOINT:-}"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "'$1' is required. See README.md (Prerequisites)."; }

outputs() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' --output table
}

deploy() {
  need aws; need sam; need python3
  aws sts get-caller-identity >/dev/null 2>&1 || die "AWS credentials not configured (run 'aws configure' or 'aws sso login')."

  log "Validating template"
  sam validate --lint --region "$AWS_REGION"

  log "Building"
  sam build

  log "Deploying stack ${STACK_NAME} to ${AWS_REGION}"
  sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --resolve-s3 \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
      "ProjectName=${PROJECT_NAME}" \
      "Environment=${ENVIRONMENT}" \
      "AlertEmail=${ALERT_EMAIL}" \
      "PeakThresholdKw=${PEAK_THRESHOLD_KW}" \
      "Timezone=${TIMEZONE}" \
      "CorsOrigin=${CORS_ORIGIN}" \
      "SageMakerEndpointName=${SAGEMAKER_ENDPOINT}"

  log "Seeding buildings and tariff windows"
  python3 edge_provision.py --stack "$STACK_NAME" --region "$AWS_REGION" seed

  log "Stack outputs"
  outputs
  cat <<MSG

Next steps:
  1. Confirm the SNS subscription email (if ALERT_EMAIL was set).
  2. Register edge gateways:  python3 edge_provision.py --stack ${STACK_NAME} --region ${AWS_REGION} provision --building lab_1
  3. Send test data:          python3 edge_provision.py --stack ${STACK_NAME} --region ${AWS_REGION} simulate --building lab_1
  4. Create a dashboard user: see README.md, section "Dashboard users".
MSG
}

destroy() {
  need aws; need python3
  read -r -p "Delete stack ${STACK_NAME} in ${AWS_REGION} and ALL its data? [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

  bucket="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='RawBucketName'].OutputValue" --output text 2>/dev/null || true)"
  if [[ -n "$bucket" && "$bucket" != "None" ]]; then
    log "Emptying bucket ${bucket} (all versions)"
    python3 - "$bucket" "$AWS_REGION" <<'PY'
import sys, boto3
bucket, region = sys.argv[1], sys.argv[2]
boto3.resource("s3", region_name=region).Bucket(bucket).object_versions.delete()
PY
  fi

  log "Deleting stack"
  aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$AWS_REGION"
  aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$AWS_REGION"
  echo "Deleted. IoT things/certificates created by edge_provision.py are not part of the stack; remove them with:"
  echo "  python3 edge_provision.py --stack ${STACK_NAME} --region ${AWS_REGION} cleanup"
}

case "${1:-deploy}" in
  deploy)  deploy ;;
  outputs) need aws; outputs ;;
  destroy) destroy ;;
  *) die "Unknown command '$1'. Use: deploy | outputs | destroy" ;;
esac
