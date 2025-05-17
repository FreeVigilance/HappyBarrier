#!/bin/sh

log() {
  level=$1
  shift
  message=$*
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "{\"time\": \"$timestamp\", \"level\": \"$level\", \"message\": \"$message\"}"
}

log info "Applying migrations..."
python manage.py migrate

log info "Collecting static files..."
python manage.py collectstatic --noinput

log info "Creating superuser if not exists..."
python manage.py shell << EOF
from users.models import User
phone = '${DJANGO_SUPERUSER_PHONE}'
full_name = '${DJANGO_SUPERUSER_NAME}'
password = '${DJANGO_SUPERUSER_PASSWORD}'

if not User.objects.filter(role=User.Role.SUPERUSER).exists():
    User.objects.create_superuser(
        phone=phone,
        password=password,
        full_name=full_name
    )
EOF

log info 'Starting Kafka consumers...'
python manage.py run_sms_consumers & >> /dev/stdout 2>&1 &

log info 'Starting scheduler...'
python manage.py run_scheduler & >> /dev/stdout 2>&1 &

log info 'Starting server...';
python manage.py runserver 0.0.0.0:8000
