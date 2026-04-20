#!/usr/bin/env python3
"""MCP server that exposes Ollama models as tools to Claude Code."""

import json
import sys
import urllib.request
import urllib.error
from typing import Any

OLLAMA_BASE_URL = "http://localhost:11434"


def ollama_request(path: str, data: dict | None = None) -> dict:
    url = f"{OLLAMA_BASE_URL}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def list_models() -> list[dict]:
    result = ollama_request("/api/tags")
    return result.get("models", [])


def chat(model: str, messages: list[dict], stream: bool = False) -> str:
    data = {"model": model, "messages": messages, "stream": stream}
    result = ollama_request("/api/chat", data)
    return result.get("message", {}).get("content", "")


def generate(model: str, prompt: str, stream: bool = False) -> str:
    data = {"model": model, "prompt": prompt, "stream": stream}
    result = ollama_request("/api/generate", data)
    return result.get("response", "")


# MCP protocol over stdio

def send(obj: dict) -> None:
    line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def handle_request(req: dict) -> dict | None:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ollama-mcp", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "ollama_list_models",
                        "description": "List all locally available Ollama models.",
                        "inputSchema": {"type": "object", "properties": {}, "required": []},
                    },
                    {
                        "name": "ollama_chat",
                        "description": "Send a chat message to a local Ollama model and get a response.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "model": {
                                    "type": "string",
                                    "description": "Ollama model name (e.g. llama3, mistral, codellama)",
                                },
                                "messages": {
                                    "type": "array",
                                    "description": "Chat messages in [{role, content}] format",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "role": {"type": "string"},
                                            "content": {"type": "string"},
                                        },
                                        "required": ["role", "content"],
                                    },
                                },
                            },
                            "required": ["model", "messages"],
                        },
                    },
                    {
                        "name": "ollama_generate",
                        "description": "Generate text from a prompt using a local Ollama model.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "model": {
                                    "type": "string",
                                    "description": "Ollama model name (e.g. llama3, mistral, codellama)",
                                },
                                "prompt": {
                                    "type": "string",
                                    "description": "The prompt to generate from",
                                },
                            },
                            "required": ["model", "prompt"],
                        },
                    },
                ]
            },
        }

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "ollama_list_models":
                models = list_models()
                text = "\n".join(
                    f"- {m['name']} ({m.get('size', 0) // 1_000_000} MB)"
                    for m in models
                ) or "No models found. Run: ollama pull <model-name>"

            elif tool_name == "ollama_chat":
                text = chat(args["model"], args["messages"])

            elif tool_name == "ollama_generate":
                text = generate(args["model"], args["prompt"])

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": text}]},
            }

        except urllib.error.URLError as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Ollama connection error: {e}. Is Ollama running? Start with: ollama serve",
                        }
                    ],
                    "isError": True,
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                },
            }

    # Notifications have no id and need no response
    if req_id is None:
        return None

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(req)
        if response is not None:
            send(response)


if __name__ == "__main__":
    main()
