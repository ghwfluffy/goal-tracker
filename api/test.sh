#!/bin/bash

set -eu -o pipefail

cd "$(dirname "$0")"

REQ_HASH="$(sha256sum requirements.txt pyproject.toml | sha256sum | awk '{print $1}')"
DIGEST_FILE=".venv-requirements.sha256"

if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate

if ! python3 - <<'PY'
import importlib.util
import sys

required_modules = [
    "alembic",
    "fastapi",
    "pydantic_settings",
    "pytest",
    "sqlalchemy",
]

missing = [module for module in required_modules if importlib.util.find_spec(module) is None]
sys.exit(1 if missing else 0)
PY
then
  python3 -m pip install -r requirements.txt
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
elif [ ! -f "${DIGEST_FILE}" ]; then
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
elif [ "${REQ_HASH}" != "$(cat "${DIGEST_FILE}")" ]; then
  python3 -m pip install -r requirements.txt
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
fi

python3 -m pytest
