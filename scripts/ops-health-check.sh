#!/bin/zsh
set -euo pipefail

PORT="${PORT:-3000}"
HOST="${HOST:-127.0.0.1}"
URL="http://$HOST:$PORT/api/health"

curl --noproxy "*" -fsS "$URL"
echo
