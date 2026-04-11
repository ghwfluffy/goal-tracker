#!/bin/bash

set -eu -o pipefail

cd "$(dirname "$0")"

DIGEST_SOURCE="package-lock.json"
if [ ! -f "${DIGEST_SOURCE}" ]; then
  DIGEST_SOURCE="package.json"
fi

REQ_HASH="$(sha256sum ${DIGEST_SOURCE} | sha256sum | awk '{print $1}')"
DIGEST_FILE=".node-deps.sha256"
NEEDS_INSTALL=0

if [ ! -d node_modules ]; then
  NEEDS_INSTALL=1
elif [ ! -f "${DIGEST_FILE}" ]; then
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
elif [ "${REQ_HASH}" != "$(cat "${DIGEST_FILE}")" ]; then
  if [ -w node_modules ]; then
    NEEDS_INSTALL=1
  else
    printf 'Skipping npm install because node_modules is not writable; using existing dependencies.\n' >&2
    printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
  fi
fi

if [ "${NEEDS_INSTALL}" -eq 1 ]; then
  npm install
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
fi

npm run test -- --run
