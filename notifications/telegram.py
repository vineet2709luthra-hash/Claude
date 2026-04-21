import requests
from config import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def notify(message: str, parse_mode: str = "Markdown") -> bool:
    """Send a notification to your Telegram. Returns True on success."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": parse_mode,
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def notify_urgent(message: str) -> bool:
    """Send urgent alert with notification sound."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": f"🚨 URGENT 🚨\n\n{message}",
                "parse_mode": "Markdown",
                "disable_notification": False,
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False
