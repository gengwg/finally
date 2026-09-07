#!/usr/bin/env bash
# Stop and remove the FinAlly container. The data volume is kept. Idempotent.
set -euo pipefail

CONTAINER=finally

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker and try again." >&2
  exit 1
fi

# docker rm -f exits 0 for a missing container, so check first
if [ -n "$(docker ps -aq -f "name=^${CONTAINER}$")" ]; then
  docker rm -f "$CONTAINER" >/dev/null
  echo "Stopped and removed container $CONTAINER."
else
  echo "Container $CONTAINER is not running."
fi

echo "Volume finally-data kept — your portfolio persists."
