#!/bin/sh

set -eu

INTERVAL_MINUTES="${BACKUP_INTERVAL_MINUTES:-360}"
INTERVAL_SECONDS="$((INTERVAL_MINUTES * 60))"

while true; do
  /opt/backup/create_backup.sh automatic
  sleep "${INTERVAL_SECONDS}"
done
