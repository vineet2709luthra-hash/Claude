from integrations.amazon.client import amazon_client
from config import config
from utils.logger import get_logger

logger = get_logger("amazon.inventory")


def get_inventory_summaries() -> list[dict]:
    """Get FBA inventory levels for all SKUs."""
    data = amazon_client.get("/fba/inventory/v1/summaries", params={
        "details": "true",
        "marketplaceIds": config.AMAZON_MARKETPLACE_ID,
        "granularityType": "Marketplace",
        "granularityId": config.AMAZON_MARKETPLACE_ID,
    })
    return data.get("payload", {}).get("inventorySummaries", [])


def get_inventory_by_sku(sku: str) -> dict | None:
    items = get_inventory_summaries()
    for item in items:
        if item.get("sellerSku") == sku:
            return item
    return None


def update_listing_quantity(sku: str, quantity: int) -> dict:
    """Update stock quantity for a seller-fulfilled listing."""
    body = {
        "productType": "SHIRT",
        "patches": [{
            "op": "replace",
            "path": "/attributes/fulfillment_availability",
            "value": [{
                "fulfillment_channel_code": "DEFAULT",
                "quantity": quantity,
            }]
        }]
    }
    return amazon_client.patch(
        f"/listings/2021-08-01/items/{config.AMAZON_SELLER_ID}/{sku}"
        f"?marketplaceIds={config.AMAZON_MARKETPLACE_ID}",
        body
    )
