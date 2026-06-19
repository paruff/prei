#!/usr/bin/env bash
# gitops-validate.sh — GitOps best-practice checks
# Run standalone or via pre-commit hook / CI workflow.
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed
#
# Usage:
#   ./scripts/gitops-validate.sh              # validate all GitOps files
#   ./scripts/gitops-validate.sh --files FILE  # validate specific files only
set -euo pipefail

# ---------------------------------------------------------------------------
# Colours (disabled when not a terminal)
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
  BOLD='\033[1m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BOLD=''; NC=''
fi

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
ERRORS=0
WARNINGS=0
VALIDATED_FILES=0
MODE="all"  # "all" or "files"
SPECIFIC_FILES=()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo -e "${BOLD}ℹ${NC}  $*"; }
pass()  { echo -e "${GREEN}✓${NC}  $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; WARNINGS=$((WARNINGS + 1)); }
fail()  { echo -e "${RED}✗${NC}  $*"; ERRORS=$((ERRORS + 1)); }
header(){ echo -e "\n${BOLD}── $* ──${NC}"; }

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --files) MODE="files"; shift; while [[ $# -gt 0 && "$1" != --* ]]; do SPECIFIC_FILES+=("$1"); shift; done ;;
    --help|-h)
      echo "Usage: $0 [--files file1 file2 ...]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# 1. Dockerfile checks
# ---------------------------------------------------------------------------
validate_dockerfile() {
  local file="$1"
  header "Dockerfile: $file"

  # Must not run as root (USER directive)
  if ! grep -qE '^\s*USER\s+\S+' "$file"; then
    fail "$file: No USER directive — container runs as root"
  else
    local user_line
    user_line=$(grep -E '^\s*USER\s+' "$file" | tail -1)
    if echo "$user_line" | grep -qE 'USER\s+root'; then
      fail "$file: USER is set to root"
    else
      pass "$file: Non-root USER directive present"
    fi
  fi

  # HEALTHCHECK recommended
  if ! grep -qE '^\s*HEALTHCHECK\s+' "$file"; then
    warn "$file: No HEALTHCHECK directive (recommended for production)"
  else
    pass "$file: HEALTHCHECK directive present"
  fi

  # Must not hardcode secrets
  local secret_patterns='(password|secret|token|api_key|apikey)\s*[:=]\s*["\x27]?[^\s"]{8,}'
  if grep -iE "$secret_patterns" "$file" | grep -v -E '^\s*#' | grep -v 'POSTGRES_PASSWORD' | grep -v 'SECRET_KEY'; then
    fail "$file: Possible hardcoded secret detected"
  else
    pass "$file: No hardcoded secrets detected"
  fi

  # Should use multi-stage build (FROM ... AS)
  local from_count
  from_count=$(grep -cE '^\s*FROM\s+' "$file" || true)
  if [ "$from_count" -lt 1 ]; then
    warn "$file: No FROM instruction found"
  elif [ "$from_count" -lt 2 ]; then
    warn "$file: Single-stage build — multi-stage recommended for smaller images"
  else
    pass "$file: Multi-stage build detected ($from_count stages)"
  fi

  # Must not use ADD when COPY suffices (only if ADD is present)
  if grep -qE '^\s*ADD\s+' "$file"; then
    warn "$file: Uses ADD — prefer COPY unless tar extraction or URL fetch is needed"
  fi

  # PIP_NO_CACHE_DIR should be set to avoid bloating image
  if grep -qE 'pip install' "$file" && ! grep -qE 'PIP_NO_CACHE_DIR' "$file"; then
    warn "$file: pip install without PIP_NO_CACHE_DIR — may bloat image"
  else
    pass "$file: pip cache handling looks correct"
  fi

  # pin base image tag (not just :latest)
  # Only check FROM lines that reference external images (contain : or /)
  local base_images
  base_images=$(grep -E '^\s*FROM\s+\S+(:|/)' "$file" || true)
  if [ -z "$base_images" ]; then
    info "$file: No external base images found"
  else
    while IFS= read -r img; do
      local tag
      tag=$(echo "$img" | sed -E 's/.*FROM\s+\S+:([^\s]+).*/\1/' || true)
      local image_name
      image_name=$(echo "$img" | sed -E 's/.*FROM\s+(\S+).*/\1/' || true)
      if [ -z "$tag" ] || [ "$tag" = "latest" ]; then
        warn "$file: Base image '$image_name' is unpinned — use a specific tag or digest"
      else
        pass "$file: Base image tag pinned: $tag"
      fi
    done <<< "$base_images"
  fi

  VALIDATED_FILES=$((VALIDATED_FILES + 1))
}

# ---------------------------------------------------------------------------
# 2. docker-compose.yml checks
# ---------------------------------------------------------------------------
validate_docker_compose() {
  local file="$1"
  header "docker-compose: $file"

  # Must not hardcode passwords (unless it's a placeholder example)
  if grep -E 'password:\s*[^$\{]' "$file" | grep -v -E '(POSTGRES_PASSWORD|:?\\?\\$)' | grep -v '^\s*#' > /dev/null 2>&1; then
    fail "$file: Possible hardcoded password in docker-compose"
  else
    pass "$file: No hardcoded passwords"
  fi

  # healthcheck on services
  local services_without_health
  services_without_health=$(python3 -c "
import yaml, sys
with open('$file') as f:
    dc = yaml.safe_load(f)
services = dc.get('services', {})
missing = [name for name, svc in services.items() if 'healthcheck' not in svc]
for m in missing:
    print(m)
" 2>/dev/null || echo "")
  if [ -n "$services_without_health" ]; then
    warn "$file: Services without healthcheck: $services_without_health"
  else
    pass "$file: All services have healthchecks"
  fi

  # Must not use :latest for service images
  if grep -E 'image:\s+\S+:latest' "$file" > /dev/null 2>&1; then
    warn "$file: Uses :latest tag for service image"
  else
    pass "$file: No :latest tags on service images"
  fi

  VALIDATED_FILES=$((VALIDATED_FILES + 1))
}

# ---------------------------------------------------------------------------
# 3. Kubernetes manifest checks (YAML)
# ---------------------------------------------------------------------------
validate_k8s_manifest() {
  local file="$1"
  header "K8s manifest: $file"

  local kind
  kind=$(grep -E '^\s*kind:\s+' "$file" | awk '{print $2}' | head -1)

  # Deployment/StatefulSet: must have resource limits
  if [[ "$kind" == "Deployment" || "$kind" == "StatefulSet" ]]; then
    if grep -q 'resources:' "$file"; then
      if grep -q 'limits:' "$file" && grep -q 'requests:' "$file"; then
        pass "$file: Resource limits and requests present"
      elif grep -q 'limits:' "$file"; then
        warn "$file: Has limits but no requests — set both for QoS"
      else
        warn "$file: resources block present but no limits — add resource limits"
      fi
    else
      fail "$file: No resources block — Kubernetes won't QoS-schedule correctly"
    fi

    # securityContext
    if grep -q 'securityContext:' "$file" || grep -q 'security_context:' "$file"; then
      pass "$file: securityContext present"
    else
      warn "$file: No securityContext — add runAsNonRoot, readOnlyRootFilesystem"
    fi

    # Image pull policy
    if grep -q 'imagePullPolicy:' "$file"; then
      pass "$file: imagePullPolicy set"
    else
      warn "$file: No imagePullPolicy — default may be :latest in some clusters"
    fi
  fi

  # Secret: must not have base64-encoded data inline (warn)
  if [[ "$kind" == "Secret" ]]; then
    if grep -q 'data:' "$file" && grep -E '[A-Za-z0-9+/]{20,}={0,2}' "$file" > /dev/null 2>&1; then
      warn "$file: Secret contains inline base64 data — use sealed-secrets or external-secrets"
    fi
  fi

  # Namespace: must not target default namespace
  if grep -q 'namespace:\s*default' "$file"; then
    warn "$file: Targets 'default' namespace — use a dedicated namespace"
  fi

  # Label recommendation
  if grep -q 'app.kubernetes.io/name:' "$file"; then
    pass "$file: Standard Kubernetes labels present"
  else
    warn "$file: No app.kubernetes.io/name label — add standard labels"
  fi

  VALIDATED_FILES=$((VALIDATED_FILES + 1))
}

# ---------------------------------------------------------------------------
# 4. Kustomize checks
# ---------------------------------------------------------------------------
validate_kustomization() {
  local file="$1"
  header "Kustomize: $file"

  # Must have resources
  if grep -q 'resources:' "$file"; then
    pass "$file: Has resources block"
  else
    warn "$file: No resources block"
  fi

  # Must not have patches AND patchesStrategicMerge (conflict)
  if grep -q 'patches:' "$file" && grep -q 'patchesStrategicMerge:' "$file"; then
    warn "$file: Uses both 'patches' and 'patchesStrategicMerge' — prefer 'patches' only"
  fi

  VALIDATED_FILES=$((VALIDATED_FILES + 1))
}

# ---------------------------------------------------------------------------
# 5. Secret detection (broad scan)
# ---------------------------------------------------------------------------
detect_secrets() {
  local file="$1"
  header "Secret scan: $file"

  # Skip binary files
  if file --mime-encoding "$file" 2>/dev/null | grep -q 'binary'; then
    info "Skipping binary file"
    return
  fi

  # Patterns that suggest secrets
  local secret_patterns=(
    'AKIA[0-9A-Z]{16}'                        # AWS Access Key
    'ghp_[A-Za-z0-9]{36}'                     # GitHub PAT
    'sk-[A-Za-z0-9]{32,}'                     # OpenAI/Stripe key
    'xox[bpsar]-[0-9a-zA-Z-]+'                # Slack token
    '-----BEGIN (RSA |EC |DSA )?PRIVATE KEY'   # Private key
    'password\s*[:=]\s*["\x27][^"\x27]{8,}'  # Password assignment
  )

  local found=0
  for pattern in "${secret_patterns[@]}"; do
    if grep -E "$pattern" "$file" 2>/dev/null | grep -v -E '^\s*#' | grep -v 'POSTGRES_PASSWORD' | grep -v 'SECRET_KEY' > /dev/null 2>&1; then
      fail "$file: Possible secret matched pattern: ${pattern:0:30}..."
      found=1
    fi
  done

  if [ "$found" -eq 0 ]; then
    pass "$file: No secrets detected"
  fi

  VALIDATED_FILES=$((VALIDATED_FILES + 1))
}

# ---------------------------------------------------------------------------
# Collect files to validate
# ---------------------------------------------------------------------------
FILES_TO_CHECK=()

if [ "$MODE" = "files" ]; then
  for f in "${SPECIFIC_FILES[@]}"; do
    [ -f "$f" ] && FILES_TO_CHECK+=("$f")
  done
else
  # Find all relevant files
  while IFS= read -r -d '' f; do
    FILES_TO_CHECK+=("$f")
  done < <(find . -type f \( \
    -name 'Dockerfile*' -o \
    -name 'docker-compose*.yml' -o \
    -name 'docker-compose*.yaml' -o \
    -name '*.k8s.yaml' -o \
    -name '*.k8s.yml' -o \
    -name 'kustomization.yaml' -o \
    -name 'kustomization.yml' \
  \) -not -path './.venv/*' -not -path './.git/*' -not -path './node_modules/*' -print0 2>/dev/null)

  # Also find manifests/ and overlays/ dirs if present
  for dir in manifests overlays; do
    if [ -d "$dir" ]; then
      while IFS= read -r -d '' f; do
        FILES_TO_CHECK+=("$f")
      done < <(find "$dir" -type f \( -name '*.yaml' -o -name '*.yml' \) -print0 2>/dev/null)
    fi
  done
fi

# ---------------------------------------------------------------------------
# Run validators
# ---------------------------------------------------------------------------
echo -e "${BOLD}GitOps Validation${NC}"
echo "─────────────────────────────────────────"

for file in "${FILES_TO_CHECK[@]}"; do
  case "$file" in
    *Dockerfile*)
      validate_dockerfile "$file"
      ;;
    *docker-compose*)
      validate_docker_compose "$file"
      ;;
    *kustomization*)
      validate_kustomization "$file"
      ;;
    *.k8s.yaml|*.k8s.yml)
      validate_k8s_manifest "$file"
      ;;
    manifests/*|overlays/*)
      if grep -qE 'kind:\s+(Deployment|StatefulSet|Service|ConfigMap|Secret|Ingress)' "$file" 2>/dev/null; then
        validate_k8s_manifest "$file"
      fi
      ;;
  esac

  # Secret detection on all YAML/ENV/Docker files (not Python)
  case "$file" in
    *Dockerfile*|*docker-compose*|*.yaml|*.yml|*.env*)
      detect_secrets "$file"
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "─────────────────────────────────────────"
echo -e "${BOLD}Results:${NC} ${VALIDATED_FILES} files validated"
echo -e "  ${GREEN}Passed:${NC} checks that passed"
if [ "$WARNINGS" -gt 0 ]; then
  echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS (non-blocking)"
fi
if [ "$ERRORS" -gt 0 ]; then
  echo -e "  ${RED}Errors:${NC} $ERRORS (blocking)"
fi
echo ""

if [ "$ERRORS" -gt 0 ]; then
  echo -e "${RED}✗ Validation failed${NC}"
  exit 1
elif [ "$WARNINGS" -gt 0 ]; then
  echo -e "${YELLOW}⚠ Validation passed with warnings${NC}"
  exit 0
else
  echo -e "${GREEN}✓ All checks passed${NC}"
  exit 0
fi
