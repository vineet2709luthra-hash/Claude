from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, Enum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class Platform(str, enum.Enum):
    AMAZON = "amazon"
    MYNTRA = "myntra"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    status = Column(String, default=OrderStatus.PENDING)
    customer_name = Column(String)
    customer_email = Column(String)
    product_id = Column(String)
    product_name = Column(String)
    size = Column(String)
    color = Column(String)
    quantity = Column(Integer, default=1)
    price = Column(Float)
    total_amount = Column(Float)
    shipping_address = Column(Text)
    tracking_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ai_processed = Column(Boolean, default=False)
    notes = Column(Text)


class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    product_name = Column(String)
    design = Column(String)
    size = Column(String)
    color = Column(String)
    quantity_available = Column(Integer, default=0)
    quantity_reserved = Column(Integer, default=0)
    reorder_threshold = Column(Integer, default=10)
    price = Column(Float)
    cost_price = Column(Float)
    last_synced = Column(DateTime, default=datetime.utcnow)


class CustomerMessage(Base):
    __tablename__ = "customer_messages"

    id = Column(String, primary_key=True)
    platform = Column(String)
    order_id = Column(String)
    customer_name = Column(String)
    customer_email = Column(String)
    subject = Column(String)
    message = Column(Text)
    ai_reply = Column(Text)
    replied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    replied_at = Column(DateTime)


class Return(Base):
    __tablename__ = "returns"

    id = Column(String, primary_key=True)
    platform = Column(String)
    order_id = Column(String)
    reason = Column(String)
    status = Column(String, default="requested")
    refund_amount = Column(Float)
    ai_decision = Column(String)
    ai_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String)
    platform = Column(String)
    old_price = Column(Float)
    new_price = Column(Float)
    reason = Column(String)
    changed_at = Column(DateTime, default=datetime.utcnow)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String)
    action = Column(String)
    details = Column(Text)
    status = Column(String)  # success | warning | error
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String)
    platform = Column(String)
    total_orders = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    total_returns = Column(Integer, default=0)
    new_messages = Column(Integer, default=0)
    low_stock_items = Column(Integer, default=0)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
