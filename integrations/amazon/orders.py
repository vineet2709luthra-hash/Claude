from datetime import datetime, timedelta
from integrations.amazon.client import amazon_client
from config import config
from utils.logger import get_logger

logger = get_logger("amazon.orders")

MARKETPLACE = config.AMAZON_MARKETPLACE_ID


def get_recent_orders(hours: int = 1) -> list[dict]:
    """Fetch orders created in the last N hours."""
    created_after = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = amazon_client.get("/orders/v0/orders", params={
        "MarketplaceIds": MARKETPLACE,
        "CreatedAfter": created_after,
        "OrderStatuses": "Unshipped,PartiallyShipped,Pending",
    })
    return data.get("payload", {}).get("Orders", [])


def get_order_details(order_id: str) -> dict:
    data = amazon_client.get(f"/orders/v0/orders/{order_id}")
    return data.get("payload", {})


def get_order_items(order_id: str) -> list[dict]:
    data = amazon_client.get(f"/orders/v0/orders/{order_id}/orderItems")
    return data.get("payload", {}).get("OrderItems", [])


def confirm_shipment(order_id: str, tracking_number: str, carrier: str = "Other") -> dict:
    """Mark an order as shipped with tracking info."""
    body = {
        "marketplaceId": MARKETPLACE,
        "packageDetail": {
            "packageReferenceId": order_id,
            "carrierCode": carrier,
            "trackingNumber": tracking_number,
            "shipDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "orderItems": [],
        }
    }
    return amazon_client.post(f"/orders/v0/orders/{order_id}/shipment", body)


def get_all_orders_by_status(status: str = "Unshipped") -> list[dict]:
    data = amazon_client.get("/orders/v0/orders", params={
        "MarketplaceIds": MARKETPLACE,
        "OrderStatuses": status,
    })
    return data.get("payload", {}).get("Orders", [])
