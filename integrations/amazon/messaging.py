from integrations.amazon.client import amazon_client
from config import config
from utils.logger import get_logger

logger = get_logger("amazon.messaging")

MARKETPLACE = config.AMAZON_MARKETPLACE_ID


def get_messaging_actions(order_id: str) -> dict:
    return amazon_client.get(
        f"/messaging/v1/orders/{order_id}",
        params={"marketplaceIds": MARKETPLACE}
    )


def send_message_to_buyer(order_id: str, subject: str, body: str) -> dict:
    """Send a message to a buyer for a specific order."""
    payload = {
        "subject": subject,
        "body": body,
    }
    return amazon_client.post(
        f"/messaging/v1/orders/{order_id}/messages/confirmCustomizationDetails"
        f"?marketplaceIds={MARKETPLACE}",
        payload
    )


def get_buyer_messages(order_id: str) -> dict:
    return amazon_client.get(
        f"/messaging/v1/orders/{order_id}/messages",
        params={"marketplaceIds": MARKETPLACE}
    )
