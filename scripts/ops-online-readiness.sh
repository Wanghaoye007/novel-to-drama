#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PRIVATE_ENV="${NOVEL_DRAMA_OPS_SECRETS:-$HOME/.novel-to-drama-ops/secrets.env}"
if [ -f "$PRIVATE_ENV" ]; then
  set -a
  source "$PRIVATE_ENV"
  set +a
fi

export NODE_ENV="${NODE_ENV:-production}"
export NOVEL_DRAMA_ONLINE_MODE="${NOVEL_DRAMA_ONLINE_MODE:-1}"
export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-0}"

if [ ! -x "node_modules/.bin/tsx" ]; then
  npm install --include=dev
fi

node_modules/.bin/tsx -e '
  import { deploymentReadiness } from "./src/lib/deployment-readiness";

  const readiness = deploymentReadiness();
  console.log(JSON.stringify(readiness, null, 2));
  process.exit(readiness.status === "ready" ? 0 : 1);
'
