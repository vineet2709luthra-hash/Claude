from datetime import datetime
from agents.base_agent import BaseAgent
from database.db import get_db
from database.models import CustomerMessage
from integrations.amazon import messaging as amazon_msg
from integrations.amazon import orders as amazon_orders
from notifications.telegram import notify


class SupportAgent(BaseAgent):
    name = "SupportAgent"
    system_prompt = """You are a customer support AI for a t-shirt business selling on Amazon and Myntra.
You are friendly, professional, and empathetic. You handle:
- Order status inquiries
- Size/fit questions
- Return and refund requests
- Complaints and escalations
- General product questions

Rules:
- Always be polite and helpful
- For return requests, be accommodating within policy (30 days, unused condition)
- For complaints, apologize sincerely and offer solutions
- Keep replies concise (under 150 words)
- Sign off as "Team [Store Name]"
Write only the reply message, nothing else."""

    def _handle_amazon_messages(self):
        try:
            # Get recent unshipped orders and check for buyer messages
            orders = amazon_orders.get_all_orders_by_status("Unshipped")
            for order in orders[:20]:  # Process last 20 orders
                order_id = order.get("AmazonOrderId", "")
                try:
                    msgs = amazon_msg.get_buyer_messages(order_id)
                    messages = msgs.get("messages", [])
                    for msg in messages:
                        msg_id = msg.get("messageId", order_id + "_msg")
                        with get_db() as db:
                            existing = db.query(CustomerMessage).filter(
                                CustomerMessage.id == msg_id
                            ).first()
                            if existing:
                                continue

                            text = msg.get("text", "")
                            ai_reply = self.ask_claude(
                                f"Customer message for order {order_id}:\n\n{text}\n\n"
                                f"Write a helpful reply."
                            )

                            record = CustomerMessage(
                                id=msg_id,
                                platform="amazon",
                                order_id=order_id,
                                message=text,
                                ai_reply=ai_reply,
                                created_at=datetime.utcnow(),
                            )
                            db.add(record)

                            try:
                                amazon_msg.send_message_to_buyer(
                                    order_id,
                                    subject="Re: Your order query",
                                    body=ai_reply,
                                )
                                record.replied = True
                                record.replied_at = datetime.utcnow()
                                self.log("reply_sent", f"Replied to Amazon order {order_id}")
                            except Exception as e:
                                self.log("reply_failed", str(e), "error")
                                notify(
                                    f"📩 *Amazon Message Needs Reply*\n"
                                    f"Order: `{order_id}`\n"
                                    f"Message: {text[:200]}\n\n"
                                    f"Suggested Reply:\n{ai_reply[:300]}"
                                )
                except Exception:
                    continue
        except Exception as e:
            self.log("amazon_support", str(e), "error")

    def run(self):
        self.logger.info("SupportAgent running...")
        self._handle_amazon_messages()
