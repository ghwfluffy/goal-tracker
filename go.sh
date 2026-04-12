#!/bin/bash

set -eu -o pipefail

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

normalize_base_path() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"

  if [ -z "${value}" ] || [ "${value}" = "/" ]; then
    printf '%s' ""
    return
  fi

  if [[ "${value}" != /* ]]; then
    value="/${value}"
  fi

  while [[ "${value}" == */ && "${value}" != "/" ]]; do
    value="${value%/}"
  done

  printf '%s' "${value}"
}

APP_BASE_PATH_NORMALIZED="$(normalize_base_path "${APP_BASE_PATH:-}")"
export APP_BASE_PATH="${APP_BASE_PATH_NORMALIZED}"
export VITE_APP_BASE_PATH="${VITE_APP_BASE_PATH:-${APP_BASE_PATH_NORMALIZED}}"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-${APP_BASE_PATH_NORMALIZED}/api/v1}"

docker compose down -t1
DOCKER_BUILDKIT=0 docker compose build
docker compose up -d
docker compose logs -f
