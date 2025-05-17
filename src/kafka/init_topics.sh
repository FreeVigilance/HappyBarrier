#!/bin/bash

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Waiting for Kafka to be available..."

RETRIES=10
until /opt/bitnami/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 \
  --list > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
  log "Kafka is unavailable - retrying..."
  sleep 2
  ((RETRIES--))
done

if [ $RETRIES -eq 0 ]; then
  log "Kafka did not become available in time. Exiting."
  exit 1
fi

log "Kafka is up. Creating topics..."

TOPICS=("sms_configuration" "sms_verification" "sms_balance" "sms_responses" "failed_messages")

for topic in "${TOPICS[@]}"; do
  log "Checking topic: $topic"

  /opt/bitnami/kafka/bin/kafka-topics.sh \
    --bootstrap-server kafka:9092 \
    --describe \
    --topic "$topic" &> /dev/null

  if [ $? -eq 0 ]; then
    log "Topic '$topic' already exists. Skipping."
  else
    log "Creating topic: $topic"
    /opt/bitnami/kafka/bin/kafka-topics.sh --create \
      --bootstrap-server kafka:9092 \
      --topic "$topic" \
      --replication-factor 1 \
      --partitions 3
  fi
done
