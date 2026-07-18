#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

docker compose \
  --env-file .env \
  -f infrastructure/docker/docker-compose.yml \
  exec \
  --user "$(id -u):$(id -g)" \
  backend \
  alembic "$@"
