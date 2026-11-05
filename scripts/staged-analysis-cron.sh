#!/usr/bin/env bash
# Operational Variant B: sequential downstream catch-up, never 3 permanent workers.
set -euo pipefail

state_dir="${FSC_STATE_DIR:-/home/sven/fsc-monitor}"
mkdir -p "$state_dir"
exec 9>"$state_dir/staged-analysis.lock"
if ! flock -n 9; then
  printf '%s SKIP reason=previous-run-active\n' "$(date -u +%FT%TZ)" >> "$state_dir/staged-analysis.log"
  exit 0
fi

log="$state_dir/staged-analysis.log"
printf '%s START staged-integrated-analysis\n' "$(date -u +%FT%TZ)" >> "$log"

# A one-shot, bounded pass. Each run audits a limited, rotating cohort.\n# Keep target batches small on 2 vCPUs so downstream analysis can finish.\n# No Evidence/Consensus/Coverage daemon is started.
if timeout --signal=TERM --kill-after=60s 30m \
    docker exec fsc-backend python /app/scripts/run_staged_analysis_catchup.py \
      --max-targets 12 --batch-size 2 --max-minutes 20 >> "$log" 2>&1; then
  printf '%s DONE status=OK\n' "$(date -u +%FT%TZ)" >> "$log"
else
  result=$?
  printf '%s DONE status=ERROR exit=%s\n' "$(date -u +%FT%TZ)" "$result" >> "$log"
  exit "$result"
fi
