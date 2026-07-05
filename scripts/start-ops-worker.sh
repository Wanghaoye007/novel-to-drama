#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PRIVATE_ENV="$HOME/.novel-to-drama-ops/secrets.env"
if [ -f "$PRIVATE_ENV" ]; then
  set -a
  source "$PRIVATE_ENV"
  set +a
fi

export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export NODE_ENV="${NODE_ENV:-production}"
export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-1}"
export NOVEL_DRAMA_AUTO_WORKER="0"
export NOVEL_DRAMA_DB_PATH="${NOVEL_DRAMA_DB_PATH:-$ROOT_DIR/db.sqlite}"
export NOVEL_DRAMA_USER_EMAIL="${NOVEL_DRAMA_USER_EMAIL:-ops@novel-drama.local}"
export NOVEL_DRAMA_TENANT_SLUG="${NOVEL_DRAMA_TENANT_SLUG:-ops-demo}"
export NOVEL_DRAMA_TENANT_NAME="${NOVEL_DRAMA_TENANT_NAME:-Ops Demo Workspace}"
export NOVEL_DRAMA_BACKFILL_LEGACY_TENANT="${NOVEL_DRAMA_BACKFILL_LEGACY_TENANT:-1}"
export NOVEL_DRAMA_REQUIRE_API_KEY="${NOVEL_DRAMA_REQUIRE_API_KEY:-0}"
export NOVEL_DRAMA_REQUIRE_CREDITS="${NOVEL_DRAMA_REQUIRE_CREDITS:-0}"
export NOVEL_DRAMA_GENERATION_VARIANT="${NOVEL_DRAMA_GENERATION_VARIANT:-drama_engine_first}"
export NOVEL_DRAMA_REPAIR_BUDGET="${NOVEL_DRAMA_REPAIR_BUDGET:-episode}"
export NOVEL_DRAMA_SCRIPT_EPISODE_FIRST="${NOVEL_DRAMA_SCRIPT_EPISODE_FIRST:-1}"
export NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS="${NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS:-240}"
export NOVEL_DRAMA_ENGINE_TIMEOUT_MS="${NOVEL_DRAMA_ENGINE_TIMEOUT_MS:-1800000}"
export NOVEL_DRAMA_RECOVER_INTERRUPTED_RUNNING="${NOVEL_DRAMA_RECOVER_INTERRUPTED_RUNNING:-1}"
export NOVEL_DRAMA_RECOVER_INTERRUPTED_OLDER_THAN_MS="${NOVEL_DRAMA_RECOVER_INTERRUPTED_OLDER_THAN_MS:-0}"

if [ -x "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" ]; then
  export NOVEL_DRAMA_PYTHON="${NOVEL_DRAMA_PYTHON:-/Library/Frameworks/Python.framework/Versions/3.14/bin/python3}"
fi

if [ ! -x "node_modules/.bin/tsx" ] || [ ! -x "node_modules/.bin/drizzle-kit" ]; then
  npm install --include=dev
fi

npm run db:migrate

JOB_ARGS=("--poll-ms" "${NOVEL_DRAMA_JOB_POLL_MS:-2000}")
if [ -n "${NOVEL_DRAMA_JOB_KIND:-}" ]; then
  JOB_ARGS=("--kind" "$NOVEL_DRAMA_JOB_KIND" "${JOB_ARGS[@]}")
fi

exec npm run jobs:watch -- "${JOB_ARGS[@]}"
