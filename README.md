# Claude Code + Ollama Integration

Run local LLMs via [Ollama](https://ollama.com) directly inside Claude Code using an MCP server.

## How it works

`ollama_mcp_server.py` implements the [MCP protocol](https://modelcontextprotocol.io) over stdio, exposing three tools to Claude Code:

| Tool | Description |
|---|---|
| `ollama_list_models` | List locally available Ollama models |
| `ollama_chat` | Chat with a model using message history |
| `ollama_generate` | Generate text from a raw prompt |

Claude Code loads the server automatically via `.claude/settings.json`.

## Prerequisites

- [Claude Code](https://claude.ai/code) installed
- [Ollama](https://ollama.com) installed and at least one model pulled

## Setup

```bash
# 1. Clone this repo
git clone https://github.com/vineet2709luthra-hash/claude.git
cd claude

# 2. Run the setup script (starts Ollama, pulls llama3 if no models exist)
bash setup.sh
```

That's it. Open Claude Code in this directory and the Ollama tools will be available.

## Manual setup

If you prefer not to use the setup script:

```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama3   # or: mistral, codellama, qwen2.5-coder, etc.
```

Then open Claude Code — it reads `.claude/settings.json` and starts the MCP server.

## Example usage in Claude Code

```
List my available Ollama models.

Ask llama3 to explain how async/await works in Python.

Use codellama to generate a Python function that sorts a list of dicts by a key.
```

## Switching models

Pull any model from the [Ollama library](https://ollama.com/library):

```bash
ollama pull codellama
ollama pull mistral
ollama pull qwen2.5-coder
```

Then ask Claude Code to use that model by name.
