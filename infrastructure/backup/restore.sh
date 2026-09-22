#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
)"
REPO_ROOT="$(
  cd "$SCRIPT_DIR/../.." && pwd
)"

ENV_FILE="${FSC_ENV_FILE:-$REPO_ROOT/.env}"
COMPOSE_FILE="$REPO_ROOT/infrastructure/docker/docker-compose.yml"
BACKUP_PATH="${1:-}"

if [[ -z "$BACKUP_PATH" ]]; then
  echo "Usage: FSC_RESTORE_CONFIRM=RESTORE bash $0 <backup.dump>" >&2
  exit 2
fi

if [[ ! -f "$BACKUP_PATH" ]]; then
  echo "Backup not found: $BACKUP_PATH" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

if [[ "${FSC_RESTORE_CONFIRM:-}" != "RESTORE" ]]; then
  echo "Restore refused. Set FSC_RESTORE_CONFIRM=RESTORE explicitly." >&2
  exit 2
fi

compose=(
  docker compose
  --env-file "$ENV_FILE"
  -f "$COMPOSE_FILE"
)

backup_dir="$(
  cd "$(dirname "$BACKUP_PATH")" && pwd
)"
backup_name="$(basename "$BACKUP_PATH")"
backup_path="$backup_dir/$backup_name"
checksum_path="$backup_path.sha256"

if [[ -f "$checksum_path" ]]; then
  echo "Verifying backup checksum..." >&2
  (
    cd "$backup_dir"
    sha256sum --check "$(basename "$checksum_path")"
  ) >&2
fi

echo "Stopping FSC application services..." >&2
"${compose[@]}" down --remove-orphans >&2

echo "Starting PostgreSQL only..." >&2
"${compose[@]}" up -d --wait postgres >&2

echo "Validating backup archive..." >&2
"${compose[@]}" exec -T postgres   pg_restore --list   < "$backup_path"   > /dev/null

echo "Restoring PostgreSQL database..." >&2
"${compose[@]}" exec -T postgres sh -ec '
  exec pg_restore \
    --clean \
    --if-exists \
    --create \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    --username="$POSTGRES_USER" \
    --dbname=postgres
' < "$backup_path"

echo "Applying any newer Alembic migrations..." >&2
"${compose[@]}" run --rm backend   alembic upgrade head >&2
"${compose[@]}" run --rm backend   alembic current >&2

echo "Restore complete. Application services remain stopped." >&2
echo "Inspect the database, then start FSC with:" >&2
echo "  docker compose --env-file '$ENV_FILE' -f '$COMPOSE_FILE' up -d --wait" >&2
