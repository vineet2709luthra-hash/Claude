from datetime import datetime, date, timedelta
from agents.base_agent import BaseAgent
from database.db import get_db
from database.models import Order, Return, CustomerMessage, InventoryItem, DailyReport, OrderStatus
from integrations.amazon import reports as amazon_reports
from notifications.telegram import notify


class AnalyticsAgent(BaseAgent):
    name = "AnalyticsAgent"
    system_prompt = """You are a business analytics AI for a t-shirt seller on Amazon and Myntra.
Generate clear, insightful daily business summaries. Include:
- Key metrics (orders, revenue, returns)
- Trends (what's selling well, what's not)
- Action items for the day
- Any warnings or opportunities
Keep it concise but complete. Use bullet points. Write in a friendly business tone."""

    def generate_daily_report(self):
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        with get_db() as db:
            # Check if report already generated today
            existing = db.query(DailyReport).filter(
                DailyReport.date == today
            ).first()
            if existing:
                return

            # Gather metrics for yesterday
            orders = db.query(Order).filter(
                Order.created_at >= yesterday,
                Order.created_at < today,
            ).all()

            amazon_orders = [o for o in orders if o.platform == "amazon"]
            myntra_orders = [o for o in orders if o.platform == "myntra"]

            amazon_revenue = sum(o.total_amount or 0 for o in amazon_orders)
            myntra_revenue = sum(o.total_amount or 0 for o in myntra_orders)

            returns = db.query(Return).filter(
                Return.created_at >= yesterday,
                Return.created_at < today,
            ).count()

            new_messages = db.query(CustomerMessage).filter(
                CustomerMessage.created_at >= yesterday,
                CustomerMessage.created_at < today,
            ).count()

            low_stock = db.query(InventoryItem).filter(
                InventoryItem.quantity_available <= InventoryItem.reorder_threshold
            ).count()

            # Build context for Claude
            top_products = {}
            for o in orders:
                key = o.product_name or "Unknown"
                top_products[key] = top_products.get(key, 0) + (o.quantity or 1)

            top_sorted = sorted(top_products.items(), key=lambda x: x[1], reverse=True)[:5]

            summary_input = (
                f"Date: {today}\n"
                f"Amazon Orders: {len(amazon_orders)} | Revenue: ₹{amazon_revenue:.2f}\n"
                f"Myntra Orders: {len(myntra_orders)} | Revenue: ₹{myntra_revenue:.2f}\n"
                f"Total Orders: {len(orders)} | Total Revenue: ₹{amazon_revenue + myntra_revenue:.2f}\n"
                f"Returns: {returns}\n"
                f"Customer Messages: {new_messages}\n"
                f"Low Stock Items: {low_stock}\n"
                f"Top Products: {top_sorted}\n\n"
                f"Generate today's business summary and action items."
            )

            summary = self.ask_claude(summary_input)

            report = DailyReport(
                date=today,
                platform="all",
                total_orders=len(orders),
                total_revenue=amazon_revenue + myntra_revenue,
                total_returns=returns,
                new_messages=new_messages,
                low_stock_items=low_stock,
                summary=summary,
            )
            db.add(report)

            notify(
                f"📊 *Daily Business Report — {today}*\n\n"
                f"📦 Orders: {len(orders)} (Amazon: {len(amazon_orders)} | Myntra: {len(myntra_orders)})\n"
                f"💰 Revenue: ₹{amazon_revenue + myntra_revenue:.2f}\n"
                f"↩️ Returns: {returns} | 💬 Messages: {new_messages}\n"
                f"⚠️ Low Stock: {low_stock} items\n\n"
                f"🤖 AI Summary:\n{summary[:500]}"
            )

            self.log("daily_report", f"Report generated for {today}")

    def run(self):
        self.logger.info("AnalyticsAgent running...")
        self.generate_daily_report()
