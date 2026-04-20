#!/usr/bin/env bash
# Sets up Ollama integration for Claude Code.
set -e

echo "=== Ollama + Claude Code Setup ==="

# Check Ollama is installed
if ! command -v ollama &>/dev/null; then
  echo "Ollama not found. Install from https://ollama.com and re-run this script."
  exit 1
fi

# Start Ollama if not running
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Starting Ollama server..."
  ollama serve &
  sleep 2
fi

echo "Ollama is running."

# Pull a default model if none exist
MODEL_COUNT=$(curl -sf http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('models',[])))" 2>/dev/null || echo "0")
if [ "$MODEL_COUNT" -eq 0 ]; then
  echo "No models found. Pulling llama3 (this may take a while)..."
  ollama pull llama3
fi

echo ""
echo "Setup complete. Available models:"
curl -sf http://localhost:11434/api/tags | python3 -c "
import sys, json
models = json.load(sys.stdin).get('models', [])
for m in models:
    size_mb = m.get('size', 0) // 1_000_000
    print(f\"  - {m['name']} ({size_mb} MB)\")
"

echo ""
echo "Claude Code will now load the Ollama MCP server automatically."
echo "Use these tools in Claude Code:"
echo "  ollama_list_models  - list available local models"
echo "  ollama_chat         - chat with a model"
echo "  ollama_generate     - generate text from a prompt"
