"""Pytest configuration for investor_app tests."""

import os
import sys

import django

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal Django configuration for tests that don't require database
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")

django.setup()
