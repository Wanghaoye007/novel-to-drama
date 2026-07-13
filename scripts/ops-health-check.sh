#!/bin/zsh
set -euo pipefail

PORT="${PORT:-3000}"
HEALTH_HOST="${OPS_HEALTH_HOST:-127.0.0.1}"
URL="http://$HEALTH_HOST:$PORT/api/health"

curl --noproxy "*" -fsS "$URL"
echo
