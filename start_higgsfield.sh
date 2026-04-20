#!/bin/bash
# Opens Higgsfield AI in Chrome

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
