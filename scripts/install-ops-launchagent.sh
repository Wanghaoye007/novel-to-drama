#!/bin/zsh
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${NOVEL_DRAMA_OPS_RUNTIME:-$HOME/.novel-to-drama-ops/app}"
PLIST_NAME="com.novel-to-drama.ops-web.plist"
PLIST_SOURCE="$RUNTIME_ROOT/ops/$PLIST_NAME"
PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"
LABEL="com.novel-to-drama.ops-web"
USER_ID="$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$RUNTIME_ROOT"

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

if [ ! -f "$PLIST_SOURCE" ]; then
  echo "Missing $PLIST_SOURCE" >&2
  exit 1
fi

cp "$PLIST_SOURCE" "$PLIST_TARGET"
chmod 644 "$PLIST_TARGET"
chmod +x "$RUNTIME_ROOT/scripts/start-ops-server.sh" "$RUNTIME_ROOT/scripts/ops-health-check.sh"

launchctl bootout "gui/$USER_ID" "$PLIST_TARGET" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$USER_ID" "$PLIST_TARGET"
launchctl kickstart -k "gui/$USER_ID/$LABEL"

echo "Installed $LABEL"
echo "Runtime: $RUNTIME_ROOT"
echo "URL: http://$(scutil --get LocalHostName 2>/dev/null || hostname -s).local:3000"
