#!/usr/bin/env sh
set -eu

python manage.py migrate --noinput

exec "$@"
