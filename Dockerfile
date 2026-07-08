# syntax=docker/dockerfile:1.7
# ↑ enables BuildKit features — put this as line 1

ARG PYTHON_VERSION=3.14

# ── Version metadata (injected by CI, or default for local dev) ────────────
ARG VERSION=0.0.0-dev
ARG COMMIT=unknown

FROM python:${PYTHON_VERSION}-slim AS base

ARG VERSION
ARG COMMIT

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PREI_VERSION=${VERSION} \
    PREI_COMMIT=${COMMIT}

# Update all OS packages to latest security patches and remove Perl
# (not needed by this Python project) to eliminate Trivy alerts:
#   #137 — perl-archive-tar path traversal via symlinks (Critical)
#   #136 — Perl heap buffer overflow through 5.43.10 (Critical)
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get remove --purge -y --auto-remove perl libperl* && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── deps layer (cached unless requirements.txt changes) ───────────────────
FROM base AS deps
# Allow pip to write to /root/.cache/pip so the BuildKit cache mount is effective
ENV PIP_NO_CACHE_DIR=0
# Install Cairo dependencies required by svglib>=1.6.0 (pycairo build)
# build-essential provides gcc needed to compile pycairo C extension
RUN apt-get update && \
    apt-get install -y --no-install-recommends libcairo2-dev build-essential && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip "setuptools>=82" "wheel>=0.46.2" && \
    pip install -r requirements.txt

# ── final image ──────────────────────────────────────────────────────────
FROM base AS runtime
ARG PYTHON_VERSION
ARG VERSION
ARG COMMIT
COPY --from=deps /usr/local/lib/python${PYTHON_VERSION} /usr/local/lib/python${PYTHON_VERSION}
COPY --from=deps /usr/local/bin /usr/local/bin
# Re-upgrade pip, setuptools, and wheel so the base image's stale dist-info is replaced.
# setuptools 79.x vendors jaraco.context 5.3.0 (CVE-2026-23949) and wheel 0.45.1
# (CVE-2026-24049); upgrading brings the patched vendored versions.
# wheel 0.45.1 (standalone) also carries CVE-2026-24049; upgrade to 0.46.2+.
RUN pip install --upgrade pip "setuptools>=82" "wheel>=0.46.2"
COPY . .

# Bake version into files so the runtime can read them without a .git dir
RUN mkdir -p /app/.meta && \
    echo -n "$VERSION" > /app/.meta/version && \
    echo -n "$COMMIT" > /app/.meta/commit && \
    echo "prei_version=$VERSION commit=$COMMIT" > /app/.meta/build-info

# OCI labels (overridden by docker/metadata-action in CI, present as defaults locally)
LABEL org.opencontainers.image.title="PREI - Real Estate Investment Analyzer" \
      org.opencontainers.image.description="Django app for passive RE investment KPIs" \
      org.opencontainers.image.vendor="paruff" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${COMMIT}" \
      org.opencontainers.image.created=""

# Never run as root
RUN addgroup --system app && adduser --system --group app && \
    mkdir -p /app/.runtime/matplotlib && \
    chown -R app:app /app
USER app
ENV HOME=/app/.runtime \
    MPLCONFIGDIR=/app/.runtime/matplotlib \
    RUN_MIGRATIONS=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import sys, urllib.request\ntry:\n  urllib.request.urlopen('http://localhost:8000/api/health/')\nexcept Exception as e:\n  print(f'health check failed: {e}', file=sys.stderr)\n  sys.exit(1)"
ENTRYPOINT ["sh", "./scripts/entrypoint.sh"]
CMD ["gunicorn", "investor_app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
# test
