#!/usr/bin/env bash
set -Eeuo pipefail

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

REPO_DIR="${FSC_REPO_DIR:-/home/sven/fsc}"
MONITOR_DIR="${FSC_MONITOR_DIR:-/home/sven/fsc-monitor}"
SQL_FILE="${FSC_QUALITY_SQL_FILE:-$REPO_DIR/scripts/production-quality-report.sql}"
POSTGRES_CONTAINER="${FSC_POSTGRES_CONTAINER:-fsc-postgres}"

mkdir -p "$MONITOR_DIR"
chmod 700 "$MONITOR_DIR"

exec 9>"$MONITOR_DIR/.quality.lock"
flock -n 9 || exit 0

{
  echo "=== $(date -u +%FT%TZ) ==="
  docker exec -i "$POSTGRES_CONTAINER" sh -c \
    'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F "|"' \
    < "$SQL_FILE"
} >> "$MONITOR_DIR/quality.log"

chmod 600 "$MONITOR_DIR/quality.log"
