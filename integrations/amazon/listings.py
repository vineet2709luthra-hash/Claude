from integrations.amazon.client import amazon_client
from config import config
from utils.logger import get_logger

logger = get_logger("amazon.listings")

SELLER_ID = config.AMAZON_SELLER_ID
MARKETPLACE = config.AMAZON_MARKETPLACE_ID


def get_listing(sku: str) -> dict:
    return amazon_client.get(
        f"/listings/2021-08-01/items/{SELLER_ID}/{sku}",
        params={"marketplaceIds": MARKETPLACE, "includedData": "attributes,summaries,issues"}
    )


def update_listing_price(sku: str, price: float, currency: str = "INR") -> dict:
    body = {
        "productType": "SHIRT",
        "patches": [{
            "op": "replace",
            "path": "/attributes/purchasable_offer",
            "value": [{
                "marketplace_id": MARKETPLACE,
                "currency": currency,
                "our_price": [{"schedule": [{"value_with_tax": price}]}],
            }]
        }]
    }
    return amazon_client.patch(
        f"/listings/2021-08-01/items/{SELLER_ID}/{sku}?marketplaceIds={MARKETPLACE}",
        body
    )


def create_listing(sku: str, product_data: dict) -> dict:
    """Create a new t-shirt listing on Amazon."""
    return amazon_client.post(
        f"/listings/2021-08-01/items/{SELLER_ID}/{sku}?marketplaceIds={MARKETPLACE}",
        product_data
    )


def delete_listing(sku: str) -> dict:
    from integrations.amazon.client import amazon_client as client
    import requests
    url = f"{client.SP_API_BASE}/listings/2021-08-01/items/{SELLER_ID}/{sku}"
    resp = requests.delete(
        url,
        headers=client._headers(),
        params={"marketplaceIds": MARKETPLACE}
    )
    resp.raise_for_status()
    return resp.json()


def get_competitive_pricing(asin: str) -> dict:
    return amazon_client.get(
        f"/products/pricing/v0/competitivePrice",
        params={
            "MarketplaceId": MARKETPLACE,
            "Asins": asin,
            "ItemType": "Asin",
        }
    )


def search_catalog(keywords: str) -> dict:
    return amazon_client.get(
        "/catalog/2022-04-01/items",
        params={
            "marketplaceIds": MARKETPLACE,
            "keywords": keywords,
            "includedData": "summaries,attributes",
        }
    )
