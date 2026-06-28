#!/usr/bin/env bash
# Export YouTube cookies from your local browser and upload to mitch-cloud VPS.
# Required for YouTube URL uploads on prod (datacenter IPs trigger bot checks).
#
# Usage (from your laptop, with SSH alias "vps" configured):
#   ./deploy/setup-youtube-cookies.sh chrome
#   ./deploy/setup-youtube-cookies.sh firefox
#
# Browsers: chrome, chromium, firefox, safari, brave, edge

set -euo pipefail

BROWSER="${1:-chrome}"
VPS_HOST="${VPS_HOST:-vps}"
REMOTE_DIR="/opt/360ws/clients/docker-app/recall-ai/secrets"
REMOTE_FILE="${REMOTE_DIR}/youtube_cookies.txt"
LOCAL_TMP="$(mktemp /tmp/youtube_cookies.XXXXXX.txt)"

cleanup() {
  rm -f "$LOCAL_TMP"
}
trap cleanup EXIT

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "ERROR: yt-dlp not found locally. Install with: pip install yt-dlp"
  exit 1
fi

echo "Exporting YouTube cookies from browser: $BROWSER"
yt-dlp --cookies-from-browser "$BROWSER" --cookies "$LOCAL_TMP" \
  --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ" >/dev/null

if [ ! -s "$LOCAL_TMP" ]; then
  echo "ERROR: Cookie export produced an empty file."
  exit 1
fi

echo "Uploading cookies to ${VPS_HOST}:${REMOTE_FILE}"
ssh "$VPS_HOST" "mkdir -p '$REMOTE_DIR' && chmod 700 '$REMOTE_DIR'"
scp "$LOCAL_TMP" "${VPS_HOST}:${REMOTE_FILE}"
ssh "$VPS_HOST" "chmod 600 '${REMOTE_FILE}'"

ENV_FILE="/opt/360ws/clients/docker-app/recall-ai/.env"
ssh "$VPS_HOST" "grep -q '^YOUTUBE_COOKIES_FILE=' '$ENV_FILE' 2>/dev/null || echo 'YOUTUBE_COOKIES_FILE=/app/secrets/youtube_cookies.txt' >> '$ENV_FILE'"

echo "Restarting recall-ai app..."
ssh "$VPS_HOST" "cd /opt/360ws/clients/docker-app/recall-ai && docker compose -f docker-compose.prod.yml up -d app"

echo "Done. Test a YouTube upload at https://recall.360web.cloud/upload/"
