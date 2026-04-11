#!/bin/bash

set -eu -o pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

"${ROOT_DIR}/api/lint.sh"
"${ROOT_DIR}/api/test.sh"
"${ROOT_DIR}/web/test.sh"
"${ROOT_DIR}/web/build.sh"
