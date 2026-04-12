#!/bin/sh

set -eu

SOURCE="${1:-manual}"
BACKUP_DIR="${BACKUP_DIR:-$(pwd)/backups}"
BACKUP_UID="${BACKUP_UID:-1000}"
BACKUP_GID="${BACKUP_GID:-1000}"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
SUFFIX="$(tr -dc 'a-z0-9' </dev/urandom | head -c 6)"
STORAGE_KEY="${TIMESTAMP}_${SOURCE}_${SUFFIX}"
FILENAME="${STORAGE_KEY}.dump"
DUMP_PATH="${BACKUP_DIR}/${FILENAME}"
MANIFEST_PATH="${BACKUP_DIR}/${STORAGE_KEY}.json"

export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

pg_dump \
  --host "${POSTGRES_HOST:?POSTGRES_HOST is required}" \
  --port "${POSTGRES_PORT:?POSTGRES_PORT is required}" \
  --username "${POSTGRES_USER:?POSTGRES_USER is required}" \
  --dbname "${POSTGRES_DB:?POSTGRES_DB is required}" \
  --format custom \
  --file "${DUMP_PATH}"

FILE_SIZE_BYTES="$(wc -c < "${DUMP_PATH}" | tr -d '[:space:]')"
SHA256="$(sha256sum "${DUMP_PATH}" | awk '{print $1}')"
CREATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

cat > "${MANIFEST_PATH}" <<EOF
{"storage_key":"${STORAGE_KEY}","filename":"${FILENAME}","created_at":"${CREATED_AT}","source":"${SOURCE}","file_size_bytes":${FILE_SIZE_BYTES},"sha256":"${SHA256}"}
EOF

chmod 0640 "${DUMP_PATH}" "${MANIFEST_PATH}"
chown "${BACKUP_UID}:${BACKUP_GID}" "${DUMP_PATH}" "${MANIFEST_PATH}"

printf '%s\n' "${STORAGE_KEY}"
