#!/bin/bash

set -eu -o pipefail

cd "$(dirname "$0")"

REQ_HASH="$(sha256sum requirements.txt pyproject.toml | sha256sum | awk '{print $1}')"
DIGEST_FILE="venv/digest.sha256"

if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate

if [ ! -f "${DIGEST_FILE}" ] || [ "${REQ_HASH}" != "$(cat "${DIGEST_FILE}")" ]; then
  python3 -m pip install -r requirements.txt
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
fi

python3 -m pytest
