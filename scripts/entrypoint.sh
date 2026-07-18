#!/usr/bin/env sh
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

# Seed demo user and sample properties (idempotent — safe to run on every start)
# Skip with SKIP_SEED=1 for CI live tests where we only need the server running
if [ "${SKIP_SEED:-0}" != "1" ]; then
    python manage.py seed_data
fi

# Collect static files for WhiteNoise manifest (required by CompressedManifestStaticFilesStorage)
# CI live tests set DEBUG=True where Django serves static files directly
if [ "${SKIP_COLLECTSTATIC:-0}" != "1" ]; then
    python manage.py collectstatic --noinput
fi

# Hand off to the container CMD so this entrypoint also works for one-off commands.
exec "$@"
