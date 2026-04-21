from datetime import datetime
from agents.base_agent import BaseAgent
from database.db import get_db
from database.models import Order
from integrations.amazon import orders as amazon_orders
from integrations.myntra import orders as myntra_orders
from notifications.telegram import notify


class OrderAgent(BaseAgent):
    name = "OrderAgent"
    system_prompt = """You are an order management AI for a t-shirt business selling on Amazon and Myntra.
Your job is to:
- Analyze new orders and flag any issues (address problems, unusual quantities, fraud signals)
- Decide if orders need special attention
- Draft customer notifications when needed
- Prioritize urgent orders
Be concise and actionable. Respond in plain text."""

    def _process_amazon_orders(self) -> int:
        new_orders = amazon_orders.get_recent_orders(hours=1)
        count = 0
        for raw in new_orders:
            order_id = raw.get("AmazonOrderId", "")
            with get_db() as db:
                existing = db.query(Order).filter(Order.id == order_id).first()
                if existing:
                    continue

                items = amazon_orders.get_order_items(order_id)
                item = items[0] if items else {}

                order = Order(
                    id=order_id,
                    platform="amazon",
                    status=raw.get("OrderStatus", "pending").lower(),
                    customer_name=raw.get("BuyerInfo", {}).get("BuyerName", ""),
                    customer_email=raw.get("BuyerInfo", {}).get("BuyerEmail", ""),
                    product_id=item.get("ASIN", ""),
                    product_name=item.get("Title", ""),
                    quantity=int(item.get("QuantityOrdered", 1)),
                    price=float(item.get("ItemPrice", {}).get("Amount", 0)),
                    total_amount=float(raw.get("OrderTotal", {}).get("Amount", 0)),
                    shipping_address=str(raw.get("ShippingAddress", {})),
                    created_at=datetime.utcnow(),
                )
                db.add(order)
                count += 1

                analysis = self.ask_claude(
                    f"New Amazon order received: Order #{order_id}, "
                    f"Product: {order.product_name}, Qty: {order.quantity}, "
                    f"Amount: ₹{order.total_amount}. "
                    f"Is there anything unusual? What action should be taken?"
                )
                order.notes = analysis
                order.ai_processed = True

                notify(
                    f"🛒 *New Amazon Order*\n"
                    f"Order: `{order_id}`\n"
                    f"Product: {order.product_name}\n"
                    f"Qty: {order.quantity} | Amount: ₹{order.total_amount}\n"
                    f"AI Note: {analysis[:200]}"
                )

        if count:
            self.log("process_amazon_orders", f"Processed {count} new Amazon orders")
        return count

    def _process_myntra_orders(self) -> int:
        try:
            pending = myntra_orders.get_pending_orders()
        except Exception as e:
            self.log("process_myntra_orders", f"Myntra API error: {e}", "error")
            return 0

        count = 0
        for raw in pending:
            order_id = str(raw.get("orderId", ""))
            with get_db() as db:
                existing = db.query(Order).filter(Order.id == order_id).first()
                if existing:
                    continue

                order = Order(
                    id=order_id,
                    platform="myntra",
                    status="pending",
                    customer_name=raw.get("customerName", ""),
                    product_id=str(raw.get("skuId", "")),
                    product_name=raw.get("productName", ""),
                    size=raw.get("size", ""),
                    color=raw.get("color", ""),
                    quantity=int(raw.get("quantity", 1)),
                    price=float(raw.get("price", 0)),
                    total_amount=float(raw.get("totalAmount", 0)),
                    shipping_address=str(raw.get("shippingAddress", {})),
                    created_at=datetime.utcnow(),
                )
                db.add(order)
                count += 1

                analysis = self.ask_claude(
                    f"New Myntra order: #{order_id}, "
                    f"Product: {order.product_name} | Size: {order.size} | Color: {order.color}, "
                    f"Amount: ₹{order.total_amount}. Any issues? Action needed?"
                )
                order.notes = analysis
                order.ai_processed = True

                notify(
                    f"👕 *New Myntra Order*\n"
                    f"Order: `{order_id}`\n"
                    f"Product: {order.product_name} ({order.size}/{order.color})\n"
                    f"Amount: ₹{order.total_amount}\n"
                    f"AI Note: {analysis[:200]}"
                )

        if count:
            self.log("process_myntra_orders", f"Processed {count} new Myntra orders")
        return count

    def run(self):
        self.logger.info("OrderAgent running...")
        amazon_count = self._process_amazon_orders()
        myntra_count = self._process_myntra_orders()
        total = amazon_count + myntra_count
        if total == 0:
            self.logger.info("No new orders.")
        return total
