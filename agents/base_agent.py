from datetime import datetime
from anthropic import Anthropic
from database.db import get_db
from database.models import AgentLog
from config import config
from utils.logger import get_logger

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)


class BaseAgent:
    name: str = "BaseAgent"
    model: str = "claude-sonnet-4-6"
    system_prompt: str = "You are an AI assistant for an e-commerce seller."

    def __init__(self):
        self.logger = get_logger(self.name)

    def ask_claude(self, user_message: str, context: str = "") -> str:
        """Send a message to Claude and get a response."""
        messages = []
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
            messages.append({"role": "assistant", "content": "Understood. I have the context."})
        messages.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text

    def log(self, action: str, details: str, status: str = "success"):
        with get_db() as db:
            db.add(AgentLog(
                agent_name=self.name,
                action=action,
                details=details,
                status=status,
                created_at=datetime.utcnow(),
            ))
        self.logger.info(f"[{status.upper()}] {action}: {details[:120]}")

    def run(self):
        raise NotImplementedError("Each agent must implement run()")
