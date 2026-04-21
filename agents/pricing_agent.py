from agents.base_agent import BaseAgent
from database.db import get_db
from database.models import InventoryItem, PriceHistory
from integrations.amazon import listings as amazon_listings
from integrations.myntra import inventory as myntra_inv
from notifications.telegram import notify


class PricingAgent(BaseAgent):
    name = "PricingAgent"
    system_prompt = """You are a pricing strategy AI for a t-shirt business on Amazon and Myntra.
Your goal is to maximize profit while staying competitive.
When given competitor prices and current stock levels, recommend the optimal selling price.
Rules:
- Never go below cost price + 20% margin
- If stock is low, slightly increase price
- If stock is high, consider a small discount to move inventory
- Consider platform fees: Amazon ~15%, Myntra ~25%
- Return ONLY a JSON object: {"recommended_price": 599, "reason": "short reason"}"""

    def _optimize_amazon_prices(self):
        with get_db() as db:
            items = db.query(InventoryItem).filter(
                InventoryItem.platform == "amazon",
                InventoryItem.price > 0,
            ).all()

            for item in items:
                try:
                    # Get competitive pricing if we have product_id (ASIN)
                    comp_data = {}
                    if item.sku:
                        try:
                            comp_data = amazon_listings.get_competitive_pricing(item.sku)
                        except Exception:
                            pass

                    response = self.ask_claude(
                        f"T-shirt SKU: {item.sku}\n"
                        f"Product: {item.product_name}\n"
                        f"Current price: ₹{item.price}\n"
                        f"Cost price: ₹{item.cost_price or 'unknown'}\n"
                        f"Stock level: {item.quantity_available} units\n"
                        f"Competitor data: {str(comp_data)[:300]}\n\n"
                        f"What price should I set?"
                    )

                    import json
                    try:
                        data = json.loads(response)
                        new_price = float(data.get("recommended_price", item.price))
                        reason = data.get("reason", "")
                    except Exception:
                        continue

                    if abs(new_price - item.price) < 5:
                        continue  # Not worth changing for tiny differences

                    amazon_listings.update_listing_price(item.sku, new_price)

                    db.add(PriceHistory(
                        sku=item.sku,
                        platform="amazon",
                        old_price=item.price,
                        new_price=new_price,
                        reason=reason,
                    ))
                    item.price = new_price
                    self.log("price_updated", f"Amazon SKU {item.sku}: ₹{item.price} → ₹{new_price}")

                except Exception as e:
                    self.log("price_update_failed", f"SKU {item.sku}: {e}", "error")

    def _optimize_myntra_prices(self):
        with get_db() as db:
            items = db.query(InventoryItem).filter(
                InventoryItem.platform == "myntra",
                InventoryItem.price > 0,
            ).all()

            for item in items:
                try:
                    response = self.ask_claude(
                        f"T-shirt SKU: {item.sku}\n"
                        f"Product: {item.product_name} | Size: {item.size}\n"
                        f"Current price: ₹{item.price}\n"
                        f"Cost price: ₹{item.cost_price or 'unknown'}\n"
                        f"Stock level: {item.quantity_available} units\n"
                        f"Platform: Myntra (25% commission)\n\n"
                        f"What price should I set?"
                    )

                    import json
                    try:
                        data = json.loads(response)
                        new_price = float(data.get("recommended_price", item.price))
                        reason = data.get("reason", "")
                    except Exception:
                        continue

                    if abs(new_price - item.price) < 5:
                        continue

                    myntra_inv.update_price(item.sku, mrp=new_price * 1.2, selling_price=new_price)

                    db.add(PriceHistory(
                        sku=item.sku,
                        platform="myntra",
                        old_price=item.price,
                        new_price=new_price,
                        reason=reason,
                    ))
                    item.price = new_price
                    self.log("price_updated", f"Myntra SKU {item.sku}: ₹{item.price} → ₹{new_price}")

                except Exception as e:
                    self.log("price_update_failed", f"Myntra SKU {item.sku}: {e}", "error")

    def run(self):
        self.logger.info("PricingAgent running...")
        self._optimize_amazon_prices()
        self._optimize_myntra_prices()
