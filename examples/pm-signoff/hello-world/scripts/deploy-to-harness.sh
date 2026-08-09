#!/usr/bin/env bash
# Deploy PM_Signoff hello world Harness resources via the Harness API.
#
# Required environment variables:
#   HARNESS_API_KEY      Harness API key with create permissions
#   HARNESS_ACCOUNT_ID   Harness account identifier
#
# Optional:
#   HARNESS_BASE_URL     Default: https://app.harness.io
#   HARNESS_ORG          Default: default
#   HARNESS_PROJECT      Default: PM_Signoff
#
# Usage:
#   ./scripts/deploy-to-harness.sh ci          # minimal CI pipeline only
#   ./scripts/deploy-to-harness.sh all         # service, env, infra, both pipelines

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
HARNESS_DIR="${ROOT_DIR}/harness"

: "${HARNESS_API_KEY:?Set HARNESS_API_KEY}"
: "${HARNESS_ACCOUNT_ID:?Set HARNESS_ACCOUNT_ID}"

HARNESS_BASE_URL="${HARNESS_BASE_URL:-https://app.harness.io}"
HARNESS_ORG="${HARNESS_ORG:-default}"
HARNESS_PROJECT="${HARNESS_PROJECT:-PM_Signoff}"

MODE="${1:-ci}"

create_pipeline() {
  local yaml_file="$1"
  local name
  name="$(basename "${yaml_file}" .yaml)"
  echo "Creating pipeline from ${name}..."

  local yaml_content
  yaml_content="$(python3 - "${yaml_file}" "${HARNESS_ORG}" "${HARNESS_PROJECT}" <<'PY'
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text()
text = text.replace("orgIdentifier: default", f"orgIdentifier: {sys.argv[2]}")
text = text.replace("projectIdentifier: PM_Signoff", f"projectIdentifier: {sys.argv[3]}")
print(text)
PY
)"

  curl -sS -f \
    -X POST \
    -H "x-api-key: ${HARNESS_API_KEY}" \
    -H "Content-Type: application/yaml" \
    "${HARNESS_BASE_URL}/pipeline/api/pipelines/v2?accountIdentifier=${HARNESS_ACCOUNT_ID}&orgIdentifier=${HARNESS_ORG}&projectIdentifier=${HARNESS_PROJECT}" \
    --data-binary "${yaml_content}"
  echo
}

create_resource() {
  local resource_type="$1"
  local yaml_file="$2"
  local name
  name="$(basename "${yaml_file}" .yaml)"
  echo "Creating ${resource_type} from ${name}..."

  local yaml_content
  yaml_content="$(python3 - "${yaml_file}" "${HARNESS_ORG}" "${HARNESS_PROJECT}" <<'PY'
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text()
text = text.replace("orgIdentifier: default", f"orgIdentifier: {sys.argv[2]}")
text = text.replace("projectIdentifier: PM_Signoff", f"projectIdentifier: {sys.argv[3]}")
print(text)
PY
)"

  curl -sS -f \
    -X POST \
    -H "x-api-key: ${HARNESS_API_KEY}" \
    -H "Content-Type: application/yaml" \
    "${HARNESS_BASE_URL}/ng/api/${resource_type}?accountIdentifier=${HARNESS_ACCOUNT_ID}&orgIdentifier=${HARNESS_ORG}&projectIdentifier=${HARNESS_PROJECT}" \
    --data-binary "${yaml_content}"
  echo
}

echo "Deploying to org=${HARNESS_ORG}, project=${HARNESS_PROJECT}"

case "${MODE}" in
  ci)
    create_pipeline "${HARNESS_DIR}/pipeline-ci.yaml"
    ;;
  all)
    create_resource "services" "${HARNESS_DIR}/service.yaml"
    create_resource "environments" "${HARNESS_DIR}/environment.yaml"
    create_resource "infrastructures" "${HARNESS_DIR}/infrastructure.yaml"
    create_pipeline "${HARNESS_DIR}/pipeline-ci.yaml"
    create_pipeline "${HARNESS_DIR}/pipeline-cicd.yaml"
    ;;
  *)
    echo "Unknown mode: ${MODE}. Use 'ci' or 'all'." >&2
    exit 1
    ;;
esac

echo "Done."
