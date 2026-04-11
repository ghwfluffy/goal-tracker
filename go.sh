#!/bin/bash

set -eux -o pipefail

docker compose down -t1
docker compose build
docker compose up -d
docker compose logs -f
