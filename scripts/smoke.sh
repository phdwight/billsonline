#!/usr/bin/env bash
# Deploy the app locally (Docker, exactly as production runs) and smoke it
# with Playwright: screenshot every page and fail on any console/page/HTTP
# error. Screenshots land in tests/smoke/screenshots/ for visual inspection.
#
# Usage: bash scripts/smoke.sh          # port 8100 by default
#        SMOKE_PORT=8200 bash scripts/smoke.sh
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=billsonline:local
NAME=billsonline-smoke
PORT="${SMOKE_PORT:-8100}"

docker build -t "$IMAGE" .

docker rm -f "$NAME" >/dev/null 2>&1 || true
# No volume: the container gets a throwaway database and --rm cleans it up.
docker run -d --rm -p "${PORT}:8000" -e SECRET_KEY=smoke-secret --name "$NAME" "$IMAGE"
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

echo "Waiting for http://127.0.0.1:${PORT} ..."
for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null

SMOKE_BASE_URL="http://127.0.0.1:${PORT}" python -m pytest tests/smoke/ -v "$@"

echo
echo "Smoke passed. Screenshots: tests/smoke/screenshots/"
