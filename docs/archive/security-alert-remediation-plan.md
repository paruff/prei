# Security Alert Remediation Plan

## Source
GitHub Code Scanning (Trivy) — 25 alerts on `main` branch.
All are OS-level CVEs in the Docker base image `python:3.14.6-slim-bookworm`.

## Root Cause
The Dockerfile pins to a specific Python image version but does not run `apt-get upgrade` after the base image is pulled. The Debian bookworm base ships with outdated system packages.

## Alerts by Category

### Critical (6 alerts)
| Alert | Package | CVE | Fix |
|-------|---------|-----|-----|
| #367 | perl | Signed integer overflow (Storable) | Already removed via `apt-get remove perl` |
| #365 | perl | Incorrect regex processing | Already removed via `apt-get remove perl` |
| #362 | zlib | Integer overflow in zipOpenNewFileInZip4_6 | `apt-get upgrade` |
| #351 | sqlite | Integer overflow | `apt-get upgrade` |
| #137 | perl-archive-tar | Path traversal via symlinks | Already removed via `apt-get remove perl` |
| #136 | perl | Heap buffer overflow on 32-bit builds | Already removed via `apt-get remove perl` |

### High (19 alerts)
| Alert | Package | Fix |
|-------|---------|-----|
| #399, #398 | openssl (QUIC DoS) | `apt-get upgrade` |
| #366 | perl (pack/unpack info disclosure) | Already removed |
| #265 | acl (symlink traversal) | `apt-get upgrade` |
| #264 | GNU gzip (buffer overflow) | `apt-get upgrade` |
| #247, #243, #239, #235, #231, #227, #223, #219 | libblkid (integer overflow ×8) | `apt-get upgrade` |
| #143 | perl-IO-Compress | Already removed |
| #139, #138 | perl-Archive-Tar | Already removed |
| #120, #118, #92 | ncurses (buffer overflow ×3) | `apt-get upgrade` |

## Fix Strategy

### Option A: Add `apt-get upgrade` to Dockerfile (Recommended)
Add `apt-get upgrade -y` to the base image build step. This pulls in security patches for all OS packages without changing the base image version.

### Option B: Upgrade Python image version
Bump `PYTHON_IMAGE_VERSION` from `3.14.6` to the latest available (e.g., `3.14.7`). This may include newer Debian packages.

### Option C: Both A + B
Upgrade image + run apt-get upgrade for maximum coverage.

## Recommendation
**Option C** — Upgrade the Python image and add `apt-get upgrade`. This resolves all alerts and provides defense-in-depth.

## Verification
After deploying the fix:
1. Rebuild the Docker image
2. Run Trivy scan locally: `trivy image prei:latest`
3. Verify all 25 alerts are resolved
4. Confirm the app still passes all tests
