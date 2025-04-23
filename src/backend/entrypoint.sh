#!/bin/sh

log() {
  level=$1
  shift
  message=$*
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "{\"time\": \"$timestamp\", \"level\": \"$level\", \"message\": \"$message\"}"
}

log info "Checking for unapplied model changes..."
python manage.py makemigrations --check --dry-run
if [ $? -ne 0 ]; then
  log error "There are model changes that are not reflected in migrations!"
  exit 1
fi

log info "No missing migrations found."

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


log info "Starting Gunicorn..."
gunicorn --bind 0.0.0.0:8000 backend.wsgi:application \
  --access-logfile - \
  --error-logfile - \
  --access-logformat '{"time": "%(t)s", "level": "INFO", "status": %(s)s, "method": "%(m)s", "url": "%(U)s", "size": %(b)s, "ip": "%(h)s", "user_agent": "%(a)s"}'
