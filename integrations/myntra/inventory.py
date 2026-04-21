from integrations.myntra.client import myntra_client
from utils.logger import get_logger

logger = get_logger("myntra.inventory")


def get_all_inventory() -> list[dict]:
    data = myntra_client.get("/v1/inventory", params={"limit": 500})
    return data.get("items", [])


def get_inventory_by_sku(sku: str) -> dict | None:
    try:
        return myntra_client.get(f"/v1/inventory/{sku}")
    except Exception:
        return None


def update_stock(sku: str, quantity: int) -> dict:
    return myntra_client.put(f"/v1/inventory/{sku}", {"quantity": quantity})


def update_price(sku: str, mrp: float, selling_price: float) -> dict:
    return myntra_client.put(f"/v1/inventory/{sku}/price", {
        "mrp": mrp,
        "sellingPrice": selling_price,
    })


def get_low_stock_items(threshold: int = 10) -> list[dict]:
    all_items = get_all_inventory()
    return [item for item in all_items if item.get("quantity", 0) <= threshold]
