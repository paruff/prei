#!/usr/bin/env bash
# Usage: ./scripts/init_django.sh <project_name>
# Initializes a minimal Django project skeleton inside the repo.
set -e
PROJECT_NAME=${1:-investor_app}

if [ -d "$PROJECT_NAME" ]; then
  echo "Directory $PROJECT_NAME already exists. Aborting."
  exit 1
fi

python -m pip install --upgrade pip
pip install -r requirements.txt

django-admin startproject "$PROJECT_NAME" .

echo "Django project '$PROJECT_NAME' created. Next steps:"
echo " - cp .env.example .env && edit .env"
echo " - python manage.py migrate"
echo " - python manage.py createsuperuser"
