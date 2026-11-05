#!/usr/bin/env bash
# Production nightly PostgreSQL backup. Cron invokes this via
# /home/sven/fsc-deploy/backup-fsc.sh for backward compatibility.
set -Eeuo pipefail

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
BACKUP_DIR=/home/sven/fsc-backups
REPO_DIR=/home/sven/fsc
OFFSITE_SCRIPT=/home/sven/fsc-deploy/offsite-restic.sh
OFFSITE_ENABLED=/home/sven/.config/fsc-backup/enabled

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

exec 9>"$BACKUP_DIR/.backup.lock"
if ! flock -n 9; then
  echo "$(date -u +%FT%TZ) backup skipped: another backup is running" >> "$BACKUP_DIR/backup.log"
  exit 0
fi

exec >>"$BACKUP_DIR/backup.log" 2>&1
echo "=== $(date -u +%FT%TZ) FSC backup start ==="

cd "$REPO_DIR"
backup_path="$(
  FSC_BACKUP_DIR="$BACKUP_DIR" bash infrastructure/backup/backup.sh
)"
printf '%s\n' "$backup_path"

if [[ -f "$OFFSITE_ENABLED" ]]; then
  echo "Uploading encrypted offsite snapshot with restic..."
  "$OFFSITE_SCRIPT" backup "$backup_path"
  "$OFFSITE_SCRIPT" check
  echo "Encrypted offsite snapshot and repository check complete."

  # Never prune on a failed/partial dump, failed upload, or failed
  # offsite repository check. The Python helper validates the kept dump
  # again and only deletes older scheduled local dumps + their checksums.
  python3 "$REPO_DIR/infrastructure/backup/prune_local_backups.py" \
    --directory "$BACKUP_DIR" \
    --keep "$backup_path" \
    --execute
else
  # The latest complete local backup must remain available even when
  # offsite protection is temporarily disabled; do not prune local history.
  echo "WARNING: Offsite backup disabled; retaining all local dumps."
fi

echo "=== $(date -u +%FT%TZ) FSC backup complete ==="
