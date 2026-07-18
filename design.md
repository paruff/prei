# Design: GitOps Phase 3 — Hardening
# Written: 2026-07-18
# Status: Draft

---

## 1. Architecture

### 1.1 GitHub Environment

```
Settings → Environments → "production"
  ├── Required reviewers: paruff
  ├── Wait timer: 0 minutes
  └── Deployment branches: main
```

The `docker-publish.yml` publish job references this environment, enforcing
approval before image publishing.

### 1.2 Image Signature Verification

The `docker-publish.yml` already uses `actions/attest-build-provenance@v4`
for Cosign keyless signing. Phase 3 adds verification in `post-deployment.yml`:

```yaml
- name: Verify image signature
  run: |
    gh attestation verify \
      "oci://${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ github.event.client_payload.image }}" \
      --repo ${{ github.repository }}
```

### 1.3 Drift Detection

`scripts/drift-check.sh` compares the deployed health endpoint with the
expected state from git manifests:

```bash
# Query deployed health
DEPLOYED=$(curl -sf "$DEPLOY_URL/health/" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")

# Expected state: "ok"
if [ "$DEPLOYED" != "ok" ]; then
  echo "::error::Drift detected: deployed health is '$DEPLOYED', expected 'ok'"
  exit 1
fi
```

For a more complete drift check (when K8s is available), compare the deployed
image digest with the gitops manifest.

---

## 2. File Changes

| File | Change | Purpose |
|---|---|---|
| `.github/workflows/docker-publish.yml` | Add `environment: production` to publish job | F-01, F-02 |
| `.github/workflows/post-deployment.yml` | Add image signature verification step | F-04 |
| `scripts/drift-check.sh` | New: drift detection script | F-05 |
| `docs/GITOPS_COMPLIANCE_AUDIT.md` | Update to mark Phase 3 complete | Documentation |