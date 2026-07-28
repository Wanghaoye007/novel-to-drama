#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PERSIST_ROOT="${NOVEL_DRAMA_PERSIST_ROOT:-/data}"
if ! mountpoint -q "$PERSIST_ROOT"; then
  echo "Persistent volume is not mounted at $PERSIST_ROOT; refusing to start." >&2
  echo "Attach one Zeabur Volume at $PERSIST_ROOT before redeploying." >&2
  exit 78
fi

export NODE_ENV=production
export PORT="${PORT:-8080}"
export HOME=/home/node
export NOVEL_DRAMA_ONLINE_MODE="${NOVEL_DRAMA_ONLINE_MODE:-1}"
export NOVEL_DRAMA_DEPLOYMENT_TARGET="${NOVEL_DRAMA_DEPLOYMENT_TARGET:-production}"
export NOVEL_DRAMA_DEPLOYMENT_AUDIENCE="${NOVEL_DRAMA_DEPLOYMENT_AUDIENCE:-internal}"
export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-0}"
export NOVEL_DRAMA_AUTO_WORKER=0
export NOVEL_DRAMA_DB_PATH="${NOVEL_DRAMA_DB_PATH:-/data/db.sqlite}"
export NOVEL_DRAMA_STORAGE_ROOT="${NOVEL_DRAMA_STORAGE_ROOT:-/data/storage}"
export NOVEL_DRAMA_BACKUP_DIR="${NOVEL_DRAMA_BACKUP_DIR:-/data/backups}"
export NOVEL_DRAMA_ACCESS_COOKIE_SECURE="${NOVEL_DRAMA_ACCESS_COOKIE_SECURE:-1}"
export NOVEL_DRAMA_ALLOW_SESSION_SWITCH="${NOVEL_DRAMA_ALLOW_SESSION_SWITCH:-0}"
export NOVEL_DRAMA_RECOVER_INTERRUPTED_RUNNING="${NOVEL_DRAMA_RECOVER_INTERRUPTED_RUNNING:-1}"
export NOVEL_DRAMA_RECOVER_INTERRUPTED_OLDER_THAN_MS="${NOVEL_DRAMA_RECOVER_INTERRUPTED_OLDER_THAN_MS:-0}"
export NPM_CONFIG_UPDATE_NOTIFIER=false

mkdir -p \
  "$(dirname "$NOVEL_DRAMA_DB_PATH")" \
  "$NOVEL_DRAMA_STORAGE_ROOT" \
  "$NOVEL_DRAMA_BACKUP_DIR"
chown -R node:node "$PERSIST_ROOT"

run_as_node() {
  gosu node "$@"
}

run_as_node npm run db:migrate:runtime
run_as_node npm run ops:backup
run_as_node npm run ops:online-readiness

WEB_PID=""
WORKER_PID=""
BACKUP_PID=""
SHUTTING_DOWN=0

shutdown() {
  if [ "$SHUTTING_DOWN" -eq 1 ]; then
    return
  fi
  SHUTTING_DOWN=1
  trap - TERM INT EXIT
  for pid in "$WEB_PID" "$WORKER_PID" "$BACKUP_PID"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}

trap shutdown TERM INT EXIT

run_as_node npm run start -- -H 0.0.0.0 -p "$PORT" &
WEB_PID=$!

run_as_node npm run jobs:watch -- --poll-ms "${NOVEL_DRAMA_JOB_POLL_MS:-2000}" --recover-interrupted &
WORKER_PID=$!

(
  while sleep "${NOVEL_DRAMA_BACKUP_INTERVAL_SECONDS:-86400}"; do
    run_as_node npm run ops:backup || echo "Scheduled backup failed; see logs." >&2
  done
) &
BACKUP_PID=$!

set +e
wait -n "$WEB_PID" "$WORKER_PID"
EXIT_CODE=$?
set -e

echo "Web or worker exited with status $EXIT_CODE; stopping the service." >&2
shutdown
exit "$EXIT_CODE"
