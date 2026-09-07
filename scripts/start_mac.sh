#!/usr/bin/env bash
# Build (if needed) and run the FinAlly container. Idempotent.
set -euo pipefail

IMAGE=finally
CONTAINER=finally
VOLUME=finally-data
URL=http://localhost:8000
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

build=false
open_browser=true
for arg in "$@"; do
  case "$arg" in
    --build) build=true ;;
    --no-open) open_browser=false ;;
    *) echo "usage: $(basename "$0") [--build] [--no-open]" >&2; exit 1 ;;
  esac
done

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker and try again." >&2
  exit 1
fi

if [ ! -f "$ROOT/.env" ]; then
  echo "Missing $ROOT/.env — copy .env.example to .env and set OPENROUTER_API_KEY." >&2
  exit 1
fi

if [ "$build" = true ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building $IMAGE..."
  docker build -t "$IMAGE" "$ROOT"
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER" \
  -p 8000:8000 \
  --env-file "$ROOT/.env" \
  -v "$VOLUME:/app/db" \
  "$IMAGE" >/dev/null

echo "FinAlly is starting at $URL"
echo "Logs: docker logs -f $CONTAINER"

if [ "$open_browser" = true ]; then
  if command -v open >/dev/null 2>&1; then
    open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  fi
fi
