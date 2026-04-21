import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Claude AI
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Amazon SP-API
    AMAZON_CLIENT_ID: str = os.getenv("AMAZON_CLIENT_ID", "")
    AMAZON_CLIENT_SECRET: str = os.getenv("AMAZON_CLIENT_SECRET", "")
    AMAZON_REFRESH_TOKEN: str = os.getenv("AMAZON_REFRESH_TOKEN", "")
    AMAZON_SELLER_ID: str = os.getenv("AMAZON_SELLER_ID", "")
    AMAZON_MARKETPLACE_ID: str = os.getenv("AMAZON_MARKETPLACE_ID", "A21TJRUUN4KGV")

    # Myntra
    MYNTRA_API_KEY: str = os.getenv("MYNTRA_API_KEY", "")
    MYNTRA_API_SECRET: str = os.getenv("MYNTRA_API_SECRET", "")
    MYNTRA_SELLER_ID: str = os.getenv("MYNTRA_SELLER_ID", "")
    MYNTRA_BASE_URL: str = "https://seller.myntra.com/api"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # App
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./seller_ai.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8000"))

    # Agent intervals (minutes)
    ORDER_CHECK_INTERVAL: int = int(os.getenv("ORDER_CHECK_INTERVAL", "15"))
    INVENTORY_CHECK_INTERVAL: int = int(os.getenv("INVENTORY_CHECK_INTERVAL", "60"))
    PRICING_CHECK_INTERVAL: int = int(os.getenv("PRICING_CHECK_INTERVAL", "120"))
    SUPPORT_CHECK_INTERVAL: int = int(os.getenv("SUPPORT_CHECK_INTERVAL", "10"))
    ANALYTICS_REPORT_TIME: str = os.getenv("ANALYTICS_REPORT_TIME", "08:00")

    def validate(self) -> list[str]:
        """Returns a list of missing critical credentials."""
        missing = []
        if not self.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not self.AMAZON_CLIENT_ID:
            missing.append("AMAZON_CLIENT_ID")
        if not self.AMAZON_REFRESH_TOKEN:
            missing.append("AMAZON_REFRESH_TOKEN")
        if not self.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN (optional but recommended)")
        return missing


config = Config()
