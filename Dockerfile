# syntax=docker/dockerfile:1.7
# ↑ enables BuildKit features — put this as line 1

FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# --- deps layer (cached unless requirements.txt changes) ---
FROM base AS deps
# Allow pip to write to /root/.cache/pip so the BuildKit cache mount is effective
ENV PIP_NO_CACHE_DIR=0
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# --- final image ---
FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . .

# Never run as root
RUN addgroup --system app && adduser --system --group app
USER app

EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]
