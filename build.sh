#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
# Reject releases whose model changes have no committed migration.
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py compilemessages
