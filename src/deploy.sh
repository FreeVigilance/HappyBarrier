#!/bin/bash

set -e

if ! command -v docker-compose &> /dev/null; then
  echo "Ошибка: docker-compose не установлен. Установите его и повторите попытку."
  exit 1
fi

echo "Generating env files from .env ..."

BACKEND_ENV="backend/prod.env"
FRONTEND_ENV="frontend/prod.env"
KAFKA_ENV="kafka/kafka.env"
KAFKA_UI_ENV="kafka/kafka-ui.env"
GRAFANA_ENV="monitoring/grafana.env"

set -a
source ".env"
set +a

DOMAINS_CSV="$SERVER_DOMAINS"
#DOMAINS_WITH_HTTPS=$(echo "$DOMAINS_CSV" | sed -E 's/([^,]+)/https:\/\/\1/g')
HOSTS_ALL=$(echo "$SERVER_DOMAINS,$SERVER_IP,localhost,127.0.0.1,0.0.0.0" \
    | tr ',' '\n' | sed '/^$/d' | paste -sd ',' -)

DOMAINS_WITH_HTTPS=$(echo "$SERVER_DOMAINS" \
    | tr ',' '\n' | sed '/^$/d' | sed 's/^/https:\/\//' | paste -sd ',' -)

HOSTS_HTTPS=$(echo "$DOMAINS_WITH_HTTPS,https://$SERVER_IP,https://localhost,https://127.0.0.1,https://0.0.0.0" \
    | tr ',' '\n' | sed '/^https:\/\/$/d' | sed '/^$/d' | paste -sd ',' -)

#HOSTS_ALL="$DOMAINS_CSV,$SERVER_IP,localhost,127.0.0.1,0.0.0.0"
#HOSTS_HTTPS="$DOMAINS_WITH_HTTPS,https://$SERVER_IP,https://localhost,https://127.0.0.1,https://0.0.0.0"

cat > "$BACKEND_ENV" <<EOF
DJANGO_SECRET_KEY='$DJANGO_SECRET_KEY'
DJANGO_ALLOWED_HOSTS='$HOSTS_ALL'
DJANGO_CSRF_TRUSTED_ORIGINS='$HOSTS_HTTPS'
DJANGO_CORS_ALLOWED_ORIGINS='$HOSTS_HTTPS'
ACCESS_TOKEN_LIFETIME_MINUTES=30
REFRESH_TOKEN_LIFETIME_DAYS=30
POSTGRES_DB='$DB_NAME'
POSTGRES_USER='$DB_USER'
POSTGRES_PASSWORD='$DB_PASSWORD'
DJANGO_SUPERUSER_PHONE='$SUPERUSER_PHONE'
DJANGO_SUPERUSER_NAME='$SUPERUSER_NAME'
DJANGO_SUPERUSER_PASSWORD='$SUPERUSER_PASSWORD'
EOF

# FRONTEND ENV
cat > "$FRONTEND_ENV" <<EOF
VITE_ALLOWED_HOSTS='$HOSTS_ALL'
EOF

# KAFKA ENV
cat > "$KAFKA_ENV" <<EOF
KAFKA_KRAFT_CLUSTER_ID='$KAFKA_KRAFT_CLUSTER_ID'
EOF

# KAFKA UI ENV
cat > "$KAFKA_UI_ENV" <<EOF
SPRING_SECURITY_USER_NAME='$SUPERUSER_PHONE'
SPRING_SECURITY_USER_PASSWORD='$SUPERUSER_PASSWORD'
EOF

# GRAFANA ENV
cat > "$GRAFANA_ENV" <<EOF
GF_SECURITY_ADMIN_USER='$SUPERUSER_PHONE'
GF_SECURITY_ADMIN_PASSWORD='$SUPERUSER_PASSWORD'
EOF

echo "Depoying..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

echo "Deploy finished!"
