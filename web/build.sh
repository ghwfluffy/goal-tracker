#!/bin/bash

set -eux -o pipefail

cd vue
npm install
npm run build
