#!/usr/bin/env bash
# Runs on mitch-cloud after rsync. Invoked by GitHub Actions (nohup) or manually.
set -euo pipefail

DEPLOY_DIR="/opt/360ws/clients/docker-app/recall-ai"
LOG_FILE="/tmp/recall-ai-deploy.log"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$DEPLOY_DIR"

rm -f .video-processor*.tar.gz* video-processor*.tar.gz db.sqlite3 2>/dev/null || true

echo "Building and starting containers..."
docker compose -f "$COMPOSE_FILE" build
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "Waiting for app to be ready..."
sleep 20

echo "Running migrations..."
docker compose -f "$COMPOSE_FILE" exec -T app python manage.py migrate --noinput || \
docker compose -f "$COMPOSE_FILE" run --rm app python manage.py migrate --noinput

echo "Collecting static files..."
docker compose -f "$COMPOSE_FILE" exec -T app python manage.py collectstatic --noinput || true

echo "Health check..."
max_attempts=30
attempt=0
while [ "$attempt" -lt "$max_attempts" ]; do
  if curl -fsS http://localhost:8030/health/ > /dev/null 2>&1; then
    echo "Health check passed!"
    if [ ! -f secrets/youtube_cookies.txt ]; then
      echo "WARNING: secrets/youtube_cookies.txt missing — YouTube URL uploads will fail (run deploy/setup-youtube-cookies.sh)"
    fi
    docker image prune -f
    docker compose -f "$COMPOSE_FILE" ps
    echo "DEPLOY_OK"
    exit 0
  fi
  attempt=$((attempt + 1))
  echo "Health check attempt $attempt/$max_attempts failed, retrying..."
  sleep 5
done

echo "DEPLOY_FAILED health check"
docker compose -f "$COMPOSE_FILE" logs app --tail=100
exit 1
