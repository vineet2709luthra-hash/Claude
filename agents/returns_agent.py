from datetime import datetime
from agents.base_agent import BaseAgent
from database.db import get_db
from database.models import Return
from integrations.myntra import returns as myntra_returns
from notifications.telegram import notify


class ReturnsAgent(BaseAgent):
    name = "ReturnsAgent"
    system_prompt = """You are a returns management AI for a t-shirt business.
Analyze return requests and decide whether to approve or reject them.

Policy:
- Approve if: within 30 days, valid reason (wrong size, defect, not as described, damaged)
- Reject if: beyond 30 days, clearly used/washed, no valid reason
- Escalate to owner if: high value order (>₹2000), suspicious pattern, unclear case

Return ONLY a JSON: {"decision": "approve"/"reject"/"escalate", "reason": "short reason", "customer_message": "message to send customer"}"""

    def _process_myntra_returns(self):
        try:
            returns = myntra_returns.get_return_requests()
        except Exception as e:
            self.log("myntra_returns", str(e), "error")
            return

        for ret in returns:
            return_id = str(ret.get("returnId", ""))
            with get_db() as db:
                existing = db.query(Return).filter(Return.id == return_id).first()
                if existing:
                    continue

                reason = ret.get("reason", "")
                order_id = str(ret.get("orderId", ""))
                amount = float(ret.get("refundAmount", 0))

                record = Return(
                    id=return_id,
                    platform="myntra",
                    order_id=order_id,
                    reason=reason,
                    refund_amount=amount,
                    created_at=datetime.utcnow(),
                )
                db.add(record)

                response = self.ask_claude(
                    f"Return request:\n"
                    f"Order ID: {order_id}\n"
                    f"Reason: {reason}\n"
                    f"Refund amount: ₹{amount}\n"
                    f"Details: {str(ret)[:400]}\n\n"
                    f"What should I do?"
                )

                import json
                try:
                    data = json.loads(response)
                    decision = data.get("decision", "escalate")
                    ai_reason = data.get("reason", "")
                    customer_msg = data.get("customer_message", "")
                except Exception:
                    decision = "escalate"
                    ai_reason = response[:200]
                    customer_msg = ""

                record.ai_decision = decision
                record.ai_notes = ai_reason

                if decision == "approve":
                    try:
                        myntra_returns.approve_return(return_id)
                        record.status = "approved"
                        record.resolved_at = datetime.utcnow()
                        self.log("return_approved", f"Return {return_id} approved: {ai_reason}")
                    except Exception as e:
                        self.log("return_approve_failed", str(e), "error")
                elif decision == "reject":
                    try:
                        myntra_returns.reject_return(return_id, ai_reason)
                        record.status = "rejected"
                        record.resolved_at = datetime.utcnow()
                        self.log("return_rejected", f"Return {return_id} rejected: {ai_reason}")
                    except Exception as e:
                        self.log("return_reject_failed", str(e), "error")
                else:
                    notify(
                        f"🔄 *Return Needs Your Decision*\n"
                        f"Return ID: `{return_id}` | Order: `{order_id}`\n"
                        f"Reason: {reason}\n"
                        f"Amount: ₹{amount}\n\n"
                        f"AI says: {ai_reason}\n"
                        f"Suggested reply: {customer_msg[:200]}"
                    )

    def run(self):
        self.logger.info("ReturnsAgent running...")
        self._process_myntra_returns()
