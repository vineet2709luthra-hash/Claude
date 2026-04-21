from integrations.myntra.client import myntra_client
from utils.logger import get_logger

logger = get_logger("myntra.orders")


def get_pending_orders() -> list[dict]:
    data = myntra_client.get("/v1/orders", params={"status": "pending", "limit": 100})
    return data.get("orders", [])


def get_order_details(order_id: str) -> dict:
    return myntra_client.get(f"/v1/orders/{order_id}")


def accept_order(order_id: str) -> dict:
    return myntra_client.post(f"/v1/orders/{order_id}/accept", {})


def ship_order(order_id: str, tracking_number: str, courier: str) -> dict:
    return myntra_client.post(f"/v1/orders/{order_id}/ship", {
        "trackingNumber": tracking_number,
        "courierName": courier,
    })


def cancel_order(order_id: str, reason: str) -> dict:
    return myntra_client.post(f"/v1/orders/{order_id}/cancel", {"reason": reason})


def get_orders_by_status(status: str) -> list[dict]:
    data = myntra_client.get("/v1/orders", params={"status": status, "limit": 100})
    return data.get("orders", [])
