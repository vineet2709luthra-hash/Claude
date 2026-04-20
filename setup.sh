#!/usr/bin/env bash
set -euo pipefail

OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_BASE_URL="http://${OLLAMA_HOST}:${OLLAMA_PORT}"

# ── Install Ollama if missing ────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  echo "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi

# ── Start Ollama server if not already running ───────────────────────────────
if ! curl -sf "${OLLAMA_BASE_URL}" &>/dev/null; then
  echo "Starting Ollama server..."
  OLLAMA_HOST="${OLLAMA_HOST}:${OLLAMA_PORT}" ollama serve &>/tmp/ollama.log &
  OLLAMA_PID=$!
  echo "Ollama PID: ${OLLAMA_PID}"

  # Wait for server to be ready (up to 30s)
  for i in $(seq 1 30); do
    if curl -sf "${OLLAMA_BASE_URL}" &>/dev/null; then
      echo "Ollama is ready."
      break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
      echo "ERROR: Ollama did not start in time. Check /tmp/ollama.log" >&2
      exit 1
    fi
  done
else
  echo "Ollama server already running at ${OLLAMA_BASE_URL}"
fi

# ── Pull the model ───────────────────────────────────────────────────────────
echo "Pulling model: ${OLLAMA_MODEL} ..."
ollama pull "${OLLAMA_MODEL}"
echo "Model ready: ${OLLAMA_MODEL}"

# ── Write .env for Claude Code / other tools ────────────────────────────────
cat > .env <<EOF
OLLAMA_MODEL=${OLLAMA_MODEL}
OLLAMA_BASE_URL=${OLLAMA_BASE_URL}
OLLAMA_OPENAI_URL=${OLLAMA_BASE_URL}/v1
EOF

echo ""
echo "Setup complete."
echo "  Model      : ${OLLAMA_MODEL}"
echo "  Ollama URL : ${OLLAMA_BASE_URL}"
echo ""
echo "Next: open Claude Code in this directory."
echo "  claude ."
