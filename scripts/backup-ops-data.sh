#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PRIVATE_ENV="${NOVEL_DRAMA_OPS_SECRETS:-$HOME/.novel-to-drama-ops/secrets.env}"
if [ -f "$PRIVATE_ENV" ]; then
  set -a
  source "$PRIVATE_ENV"
  set +a
fi

DB_PATH="${NOVEL_DRAMA_DB_PATH:-$ROOT_DIR/db.sqlite}"
STORAGE_ROOT="${NOVEL_DRAMA_STORAGE_ROOT:-$ROOT_DIR/storage}"
BACKUP_DIR="${NOVEL_DRAMA_BACKUP_DIR:-$HOME/.novel-to-drama-ops/backups}"
RETENTION_DAYS="${NOVEL_DRAMA_BACKUP_RETENTION_DAYS:-14}"
LOCK_DIR="$BACKUP_DIR/.backup.lock"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DB_BACKUP="$BACKUP_DIR/novel-drama-$STAMP.sqlite"
ASSET_BACKUP="$BACKUP_DIR/novel-drama-assets-$STAMP.tar.gz"
CHECKSUMS="$BACKUP_DIR/novel-drama-$STAMP.sha256"

if [ ! -f "$DB_PATH" ]; then
  echo "Database not found: $DB_PATH" >&2
  exit 2
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Backup already running" >&2
  exit 3
fi
trap 'rm -rf "$LOCK_DIR"' EXIT

TEMP_DB="$DB_BACKUP.tmp"
TEMP_ASSETS="$ASSET_BACKUP.tmp"
rm -f "$TEMP_DB" "$TEMP_ASSETS"
sqlite3 "$DB_PATH" ".timeout 10000" ".backup '$TEMP_DB'"
mv "$TEMP_DB" "$DB_BACKUP"

if [ -d "$STORAGE_ROOT" ]; then
  tar -czf "$TEMP_ASSETS" -C "$STORAGE_ROOT" .
else
  tar -czf "$TEMP_ASSETS" --files-from /dev/null
fi
mv "$TEMP_ASSETS" "$ASSET_BACKUP"

DB_NAME="${DB_BACKUP##*/}"
ASSET_NAME="${ASSET_BACKUP##*/}"
if command -v shasum >/dev/null 2>&1; then
  (cd "$BACKUP_DIR" && shasum -a 256 "$DB_NAME" "$ASSET_NAME") > "$CHECKSUMS"
else
  (cd "$BACKUP_DIR" && sha256sum "$DB_NAME" "$ASSET_NAME") > "$CHECKSUMS"
fi
chmod 600 "$DB_BACKUP" "$ASSET_BACKUP" "$CHECKSUMS"

find "$BACKUP_DIR" -type f \
  \( -name 'novel-drama-*.sqlite' -o -name 'novel-drama-assets-*.tar.gz' -o -name 'novel-drama-*.sha256' \) \
  -mtime "+$RETENTION_DAYS" -delete

echo "Backup complete: $DB_BACKUP"
