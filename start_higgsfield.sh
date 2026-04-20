#!/bin/bash
# Opens Higgsfield AI in Chrome with API key from .env

ENV_FILE="$(dirname "$0")/.env"
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [[ -z "$HIGGSFIELD_API_KEY" ]]; then
    echo "Error: HIGGSFIELD_API_KEY not set. Add it to .env"
    exit 1
fi

URL="https://higgsfield.ai"

if command -v google-chrome &>/dev/null; then
    google-chrome "$URL"
elif command -v google-chrome-stable &>/dev/null; then
    google-chrome-stable "$URL"
elif command -v chromium-browser &>/dev/null; then
    chromium-browser "$URL"
elif command -v chromium &>/dev/null; then
    chromium "$URL"
else
    echo "Chrome not found. Please install Google Chrome."
    exit 1
fi
