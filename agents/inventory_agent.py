from agents.base_agent import BaseAgent
from database.db import get_db
from database.models import InventoryItem
from integrations.amazon import inventory as amazon_inv
from integrations.myntra import inventory as myntra_inv
from notifications.telegram import notify


class InventoryAgent(BaseAgent):
    name = "InventoryAgent"
    system_prompt = """You are an inventory management AI for a t-shirt business on Amazon and Myntra.
Your job is to monitor stock levels, identify items running low, and recommend restocking actions.
Be specific: mention exact SKUs, quantities, and urgency level (critical/warning/ok).
Format your response clearly."""

    def _sync_amazon_inventory(self):
        try:
            items = amazon_inv.get_inventory_summaries()
        except Exception as e:
            self.log("sync_amazon", f"Failed: {e}", "error")
            return

        with get_db() as db:
            for item in items:
                sku = item.get("sellerSku", "")
                qty = item.get("inventoryDetails", {}).get("fulfillableQuantity", 0)
                existing = db.query(InventoryItem).filter(
                    InventoryItem.sku == sku,
                    InventoryItem.platform == "amazon"
                ).first()
                if existing:
                    existing.quantity_available = qty
                else:
                    db.add(InventoryItem(
                        sku=sku,
                        platform="amazon",
                        product_name=item.get("productName", ""),
                        quantity_available=qty,
                    ))

        self.log("sync_amazon", f"Synced {len(items)} Amazon inventory items")

    def _sync_myntra_inventory(self):
        try:
            items = myntra_inv.get_all_inventory()
        except Exception as e:
            self.log("sync_myntra", f"Failed: {e}", "error")
            return

        with get_db() as db:
            for item in items:
                sku = str(item.get("sku", ""))
                qty = int(item.get("quantity", 0))
                existing = db.query(InventoryItem).filter(
                    InventoryItem.sku == sku,
                    InventoryItem.platform == "myntra"
                ).first()
                if existing:
                    existing.quantity_available = qty
                else:
                    db.add(InventoryItem(
                        sku=sku,
                        platform="myntra",
                        product_name=item.get("productName", ""),
                        size=item.get("size", ""),
                        color=item.get("color", ""),
                        quantity_available=qty,
                        price=float(item.get("price", 0)),
                    ))

        self.log("sync_myntra", f"Synced {len(items)} Myntra inventory items")

    def _check_low_stock(self):
        with get_db() as db:
            low = db.query(InventoryItem).filter(
                InventoryItem.quantity_available <= InventoryItem.reorder_threshold
            ).all()

            if not low:
                return

            low_summary = "\n".join([
                f"- {i.platform.upper()} | SKU: {i.sku} | {i.product_name} | "
                f"Size: {i.size} | Qty: {i.quantity_available} (threshold: {i.reorder_threshold})"
                for i in low
            ])

            advice = self.ask_claude(
                f"These t-shirt SKUs are running low on stock:\n{low_summary}\n\n"
                f"Which ones are most urgent to restock? What quantities would you recommend ordering? "
                f"Consider that t-shirts need 3-7 days to restock."
            )

            notify(
                f"⚠️ *Low Stock Alert* — {len(low)} items\n\n"
                f"{low_summary[:400]}\n\n"
                f"💡 AI Recommendation:\n{advice[:300]}"
            )

            self.log("low_stock_check", f"{len(low)} items below threshold", "warning")

    def run(self):
        self.logger.info("InventoryAgent running...")
        self._sync_amazon_inventory()
        self._sync_myntra_inventory()
        self._check_low_stock()
