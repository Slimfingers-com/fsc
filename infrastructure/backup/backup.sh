#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")"
  && pwd
)"
REPO_ROOT="$(
  cd "$SCRIPT_DIR/../.."
  && pwd
)"

ENV_FILE="${FSC_ENV_FILE:-$REPO_ROOT/.env}"
COMPOSE_FILE="$REPO_ROOT/infrastructure/docker/docker-compose.yml"
BACKUP_DIR="${FSC_BACKUP_DIR:-$REPO_ROOT/backups}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

compose=(
  docker compose
  --env-file "$ENV_FILE"
  -f "$COMPOSE_FILE"
)

umask 077
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/fsc-$timestamp.dump"
temporary="$target.tmp.$$"

cleanup() {
  rm -f "$temporary"
}
trap cleanup EXIT

echo "Ensuring PostgreSQL is healthy..." >&2
"${compose[@]}" up -d --wait postgres >&2

echo "Creating PostgreSQL backup..." >&2
"${compose[@]}" exec -T postgres sh -ec '
  exec pg_dump
    --format=custom
    --create
    --no-owner
    --no-privileges
    --username="$POSTGRES_USER"
    --dbname="$POSTGRES_DB"
' > "$temporary"

if [[ ! -s "$temporary" ]]; then
  echo "Backup is empty." >&2
  exit 1
fi

echo "Validating backup archive..." >&2
"${compose[@]}" exec -T postgres   pg_restore --list   < "$temporary"   > /dev/null

chmod 600 "$temporary"
mv "$temporary" "$target"

(
  cd "$BACKUP_DIR"
  sha256sum "$(basename "$target")"     > "$(basename "$target").sha256"
)
chmod 600 "$target.sha256"

trap - EXIT

echo "Backup created: $target" >&2
printf '%s\n' "$target"
