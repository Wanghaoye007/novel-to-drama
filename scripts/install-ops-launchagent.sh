#!/bin/zsh
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${NOVEL_DRAMA_OPS_RUNTIME:-$HOME/.novel-to-drama-ops/app}"
PLIST_NAMES=(
  "com.novel-to-drama.ops-web.plist"
  "com.novel-to-drama.ops-worker.plist"
  "com.novel-to-drama.ops-quality-worker.plist"
  "com.novel-to-drama.ops-delivery-worker.plist"
  "com.novel-to-drama.ops-video-brief-worker.plist"
  "com.novel-to-drama.ops-localization-worker.plist"
  "com.novel-to-drama.ops-episode-optimize-worker.plist"
  "com.novel-to-drama.ops-edit-impact-worker.plist"
  "com.novel-to-drama.ops-backup.plist"
)
USER_ID="$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$RUNTIME_ROOT"

if [ "${NOVEL_DRAMA_FORCE_DEPLOY_DURING_JOBS:-0}" != "1" ] && [ -f "$RUNTIME_ROOT/db.sqlite" ]; then
  ACTIVE_JOBS="$(
    RUNTIME_ROOT="$RUNTIME_ROOT" python3 - <<'PY'
import os
import sqlite3

db_path = os.path.join(os.environ["RUNTIME_ROOT"], "db.sqlite")
try:
    connection = sqlite3.connect(db_path)
    rows = connection.execute(
        """
        select title, kind, updated_at
        from jobs
        where status = 'running'
        order by datetime(updated_at) desc
        limit 10
        """
    ).fetchall()
finally:
    try:
        connection.close()
    except Exception:
        pass

for title, kind, updated_at in rows:
    print(f"{kind}\t{updated_at}\t{title}")
PY
  )"
  if [ -n "$ACTIVE_JOBS" ]; then
    cat >&2 <<EOF
Refusing to deploy while jobs are running.

Active jobs:
$ACTIVE_JOBS

Wait for the current round to finish, or set NOVEL_DRAMA_FORCE_DEPLOY_DURING_JOBS=1 to force.
EOF
    exit 3
  fi
fi

rsync -a --delete \
  --exclude ".git/" \
  --exclude ".next/" \
  --exclude "node_modules/" \
  --exclude "logs/" \
  --exclude "storage/" \
  --exclude ".drama_mock/" \
  --exclude ".pytest_cache/" \
  --exclude "*.sqlite" \
  --exclude "*.sqlite-shm" \
  --exclude "*.sqlite-wal" \
  --exclude "*.sqlite-journal" \
  "$SOURCE_ROOT/" "$RUNTIME_ROOT/"

mkdir -p "$RUNTIME_ROOT/logs"
rm -rf "$RUNTIME_ROOT/.next"

chmod +x \
  "$RUNTIME_ROOT/scripts/start-ops-server.sh" \
  "$RUNTIME_ROOT/scripts/start-ops-worker.sh" \
  "$RUNTIME_ROOT/scripts/ops-health-check.sh" \
  "$RUNTIME_ROOT/scripts/ops-online-readiness.sh" \
  "$RUNTIME_ROOT/scripts/backup-ops-data.sh"

"$RUNTIME_ROOT/scripts/backup-ops-data.sh"

for PLIST_NAME in "${PLIST_NAMES[@]}"; do
  PLIST_SOURCE="$RUNTIME_ROOT/ops/$PLIST_NAME"
  PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"
  LABEL="${PLIST_NAME%.plist}"

  if [ ! -f "$PLIST_SOURCE" ]; then
    echo "Missing $PLIST_SOURCE" >&2
    exit 1
  fi

  cp "$PLIST_SOURCE" "$PLIST_TARGET"
  chmod 644 "$PLIST_TARGET"

  launchctl bootout "gui/$USER_ID" "$PLIST_TARGET" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$USER_ID" "$PLIST_TARGET"
  launchctl kickstart -k "gui/$USER_ID/$LABEL"

  echo "Installed $LABEL"
done
echo "Runtime: $RUNTIME_ROOT"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
LOCAL_NAME="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
if [ -n "$LAN_IP" ]; then
  echo "URL: http://$LAN_IP:3000"
  echo "mDNS fallback: http://$LOCAL_NAME.local:3000"
else
  echo "URL: http://$LOCAL_NAME.local:3000"
fi
