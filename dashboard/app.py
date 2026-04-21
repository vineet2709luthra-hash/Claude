from datetime import datetime, date, timedelta
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy import func
from database.db import get_db
from database.models import Order, InventoryItem, Return, CustomerMessage, AgentLog
import os

app = FastAPI(title="Seller AI Dashboard")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def _get_stats() -> dict:
    today = datetime.combine(date.today(), datetime.min.time())
    with get_db() as db:
        today_orders = db.query(Order).filter(Order.created_at >= today).all()
        pending = db.query(Order).filter(Order.status == "pending").count()
        low_stock = db.query(InventoryItem).filter(
            InventoryItem.quantity_available <= InventoryItem.reorder_threshold
        ).count()
        open_returns = db.query(Return).filter(Return.status == "requested").count()
        unanswered = db.query(CustomerMessage).filter(CustomerMessage.replied == False).count()

        return {
            "today_orders": len(today_orders),
            "amazon_orders": sum(1 for o in today_orders if o.platform == "amazon"),
            "myntra_orders": sum(1 for o in today_orders if o.platform == "myntra"),
            "today_revenue": f"{sum(o.total_amount or 0 for o in today_orders):,.0f}",
            "pending_orders": pending,
            "low_stock": low_stock,
            "open_returns": open_returns,
            "unanswered_messages": unanswered,
        }


def _get_agent_statuses() -> list[dict]:
    agents = [
        {"name": "Order Agent", "icon": "📦", "job": "order_agent"},
        {"name": "Inventory Agent", "icon": "🗃️", "job": "inventory_agent"},
        {"name": "Support Agent", "icon": "💬", "job": "support_agent"},
        {"name": "Pricing Agent", "icon": "💰", "job": "pricing_agent"},
        {"name": "Returns Agent", "icon": "↩️", "job": "returns_agent"},
        {"name": "Analytics Agent", "icon": "📊", "job": "analytics_agent"},
        {"name": "Account Agent", "icon": "🛡️", "job": "account_agent"},
    ]
    with get_db() as db:
        for agent in agents:
            last = db.query(AgentLog).filter(
                AgentLog.agent_name.ilike(f"%{agent['name'].replace(' Agent','').strip()}%")
            ).order_by(AgentLog.created_at.desc()).first()
            if last:
                agent["status"] = "active"
                agent["last_run"] = last.created_at.strftime("%H:%M") if last.created_at else "—"
            else:
                agent["status"] = "waiting"
                agent["last_run"] = "not run yet"
    return agents


@app.get("/")
async def dashboard(request: Request):
    stats = _get_stats()
    agent_statuses = _get_agent_statuses()

    with get_db() as db:
        orders = db.query(Order).order_by(Order.created_at.desc()).limit(20).all()
        logs = db.query(AgentLog).order_by(AgentLog.created_at.desc()).limit(30).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "agents": agent_statuses,
        "orders": orders,
        "logs": logs,
    })


@app.get("/api/stats")
async def api_stats():
    return JSONResponse(_get_stats())


@app.get("/api/orders")
async def api_orders(limit: int = 50, platform: str = None):
    with get_db() as db:
        q = db.query(Order)
        if platform:
            q = q.filter(Order.platform == platform)
        orders = q.order_by(Order.created_at.desc()).limit(limit).all()
        return JSONResponse([{
            "id": o.id, "platform": o.platform, "status": o.status,
            "product": o.product_name, "amount": o.total_amount,
            "created_at": str(o.created_at),
        } for o in orders])


@app.get("/api/inventory")
async def api_inventory(low_stock_only: bool = False):
    with get_db() as db:
        q = db.query(InventoryItem)
        if low_stock_only:
            q = q.filter(InventoryItem.quantity_available <= InventoryItem.reorder_threshold)
        items = q.all()
        return JSONResponse([{
            "sku": i.sku, "platform": i.platform, "product": i.product_name,
            "size": i.size, "color": i.color, "quantity": i.quantity_available,
            "threshold": i.reorder_threshold, "price": i.price,
        } for i in items])


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
