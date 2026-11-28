#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
# Reject releases whose model changes have no committed migration.
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
# The live service keeps database connections open while this build runs, and
# a schema change waits for them. Give up after 30 seconds so a blocked
# migration fails the deploy (the old release keeps serving) instead of
# hanging for an hour. Retry the deploy after restarting the service.
PGOPTIONS="-c lock_timeout=30s" python manage.py migrate
python manage.py compilemessages
