#!/bin/bash
# Django project initialization script

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <app_name>"
    exit 1
fi

APP_NAME="$1"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Django and dependencies
pip install --upgrade pip
pip install django numpy-financial pytest pytest-django

# Create Django project if manage.py doesn't exist
if [ ! -f "manage.py" ]; then
    django-admin startproject config .
fi

# Create the app if it doesn't exist
if [ ! -d "$APP_NAME" ]; then
    python manage.py startapp "$APP_NAME"
fi

# Create finance module directory
mkdir -p "$APP_NAME/finance"
touch "$APP_NAME/finance/__init__.py"

echo "Django project initialized with app: $APP_NAME"
