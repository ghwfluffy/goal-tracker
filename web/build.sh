#!/bin/bash

set -eu -o pipefail

cd "$(dirname "$0")"

DIGEST_SOURCE="package.json"
if [ -f package-lock.json ]; then
  DIGEST_SOURCE="${DIGEST_SOURCE} package-lock.json"
fi

REQ_HASH="$(sha256sum ${DIGEST_SOURCE} | sha256sum | awk '{print $1}')"
DIGEST_FILE="node_modules/.digest.sha256"

if [ ! -d node_modules ]; then
  npm install
  mkdir -p node_modules
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
fi

if [ ! -f "${DIGEST_FILE}" ] || [ "${REQ_HASH}" != "$(cat "${DIGEST_FILE}")" ]; then
  npm install
  mkdir -p node_modules
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
fi

npm run build
