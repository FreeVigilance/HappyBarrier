#!/bin/bash

set -e

if ! command -v docker-compose &> /dev/null; then
  echo "Ошибка: docker-compose не установлен. Установите его и повторите попытку."
  exit 1
fi

echo "Loading from .env ..."
set -a
source "prod..env"
set +a


echo "Depoying..."
cd sms_service
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

echo "Deploy finished!"
