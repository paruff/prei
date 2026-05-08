#!/usr/bin/env sh
set -e

python manage.py migrate --noinput

# Hand off to the container CMD so this entrypoint also works for one-off commands.
exec "$@"
