#!/usr/bin/env sh
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

# Collect static files for WhiteNoise manifest (required by CompressedManifestStaticFilesStorage)
python manage.py collectstatic --noinput

# Hand off to the container CMD so this entrypoint also works for one-off commands.
exec "$@"
