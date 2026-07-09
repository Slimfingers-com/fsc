#!/bin/bash

docker compose \
  --env-file .env \
  -f infrastructure/docker/docker-compose.yml \
  "$@"
