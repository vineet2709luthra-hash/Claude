from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from config import config
from utils.logger import get_logger

logger = get_logger("scheduler")


def _run_agent(agent_class):
    try:
        agent = agent_class()
        agent.run()
    except Exception as e:
        logger.error(f"Agent {agent_class.__name__} crashed: {e}", exc_info=True)


def create_scheduler() -> BackgroundScheduler:
    from agents.order_agent import OrderAgent
    from agents.inventory_agent import InventoryAgent
    from agents.support_agent import SupportAgent
    from agents.pricing_agent import PricingAgent
    from agents.returns_agent import ReturnsAgent
    from agents.analytics_agent import AnalyticsAgent
    from agents.account_agent import AccountAgent

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Orders: every N minutes (default 15)
    scheduler.add_job(
        lambda: _run_agent(OrderAgent),
        IntervalTrigger(minutes=config.ORDER_CHECK_INTERVAL),
        id="order_agent",
        name="Order Monitor",
        replace_existing=True,
    )

    # Inventory sync: every hour
    scheduler.add_job(
        lambda: _run_agent(InventoryAgent),
        IntervalTrigger(minutes=config.INVENTORY_CHECK_INTERVAL),
        id="inventory_agent",
        name="Inventory Sync",
        replace_existing=True,
    )

    # Customer support: every 10 minutes
    scheduler.add_job(
        lambda: _run_agent(SupportAgent),
        IntervalTrigger(minutes=config.SUPPORT_CHECK_INTERVAL),
        id="support_agent",
        name="Customer Support",
        replace_existing=True,
    )

    # Pricing: every 2 hours
    scheduler.add_job(
        lambda: _run_agent(PricingAgent),
        IntervalTrigger(minutes=config.PRICING_CHECK_INTERVAL),
        id="pricing_agent",
        name="Pricing Optimizer",
        replace_existing=True,
    )

    # Returns: every 30 minutes
    scheduler.add_job(
        lambda: _run_agent(ReturnsAgent),
        IntervalTrigger(minutes=30),
        id="returns_agent",
        name="Returns Manager",
        replace_existing=True,
    )

    # Daily report: every morning at configured time
    report_hour, report_minute = config.ANALYTICS_REPORT_TIME.split(":")
    scheduler.add_job(
        lambda: _run_agent(AnalyticsAgent),
        CronTrigger(hour=int(report_hour), minute=int(report_minute), timezone="Asia/Kolkata"),
        id="analytics_agent",
        name="Daily Analytics",
        replace_existing=True,
    )

    # Account health: twice a day
    scheduler.add_job(
        lambda: _run_agent(AccountAgent),
        CronTrigger(hour="9,18", minute=0, timezone="Asia/Kolkata"),
        id="account_agent",
        name="Account Health",
        replace_existing=True,
    )

    return scheduler
