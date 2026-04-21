from agents.base_agent import BaseAgent
from integrations.amazon.client import amazon_client
from config import config
from notifications.telegram import notify


class AccountAgent(BaseAgent):
    name = "AccountAgent"
    system_prompt = """You are an account health monitoring AI for an Amazon and Myntra seller.
Monitor account metrics and alert the seller about:
- Order defect rate (should be <1%)
- Late shipment rate (should be <4%)
- Pre-fulfillment cancel rate (should be <2.5%)
- Customer feedback and ratings
- Policy violations or warnings
- Suspension risks

If any metric is in the danger zone, explain clearly what it means and what action to take.
Be urgent when necessary."""

    def _check_amazon_account_health(self):
        try:
            data = amazon_client.get(
                "/sales/v1/orderMetrics",
                params={
                    "marketplaceIds": config.AMAZON_MARKETPLACE_ID,
                    "interval": "DAY",
                    "granularity": "Day",
                    "granularityTimeZone": "Asia/Kolkata",
                }
            )

            analysis = self.ask_claude(
                f"Amazon account metrics data:\n{str(data)[:800]}\n\n"
                f"Is my account health good? Any warnings or actions needed?"
            )

            if any(word in analysis.lower() for word in ["warning", "danger", "risk", "violation", "suspend"]):
                notify(f"🚨 *Amazon Account Health Alert*\n\n{analysis[:500]}")
                self.log("account_health", f"Warning detected: {analysis[:200]}", "warning")
            else:
                self.log("account_health", "Amazon account health OK")

        except Exception as e:
            self.log("account_health_check", f"Failed: {e}", "error")

    def _check_seller_feedback(self):
        try:
            data = amazon_client.get(
                "/sellers/v1/marketplaceParticipations"
            )
            self.log("feedback_check", "Checked seller participation data")
        except Exception as e:
            self.log("feedback_check", f"Failed: {e}", "error")

    def run(self):
        self.logger.info("AccountAgent running...")
        self._check_amazon_account_health()
        self._check_seller_feedback()
