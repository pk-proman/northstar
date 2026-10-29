from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Numeric, Integer, Boolean, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class CapitalTransaction(Base):
    __tablename__ = "capital_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2), nullable=False)
    reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class RiskSettings(Base):
    __tablename__ = "risk_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    max_capital: Mapped[Decimal] = mapped_column(Numeric(18,2), nullable=False)
    max_daily_loss: Mapped[Decimal] = mapped_column(Numeric(18,2), nullable=False)
    max_risk_per_trade_pct: Mapped[Decimal] = mapped_column(Numeric(8,4), nullable=False)
    max_open_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    cash_reserve_pct: Mapped[Decimal] = mapped_column(Numeric(8,4), nullable=False)
    halted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

class PaperOrder(Base):
    __tablename__ = "paper_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_order_ref: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    instrument: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(8), default="NSE", nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(12), default="MARKET", nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_price: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False)
    entry_fill_price: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False)
    mark_price: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False)
    exit_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(18,4), nullable=True)
    gross_pnl: Mapped[Decimal] = mapped_column(Numeric(18,2), default=Decimal("0"), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(18,2), default=Decimal("0"), nullable=False)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(18,2), default=Decimal("0"), nullable=False)
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    strategy_name: Mapped[str] = mapped_column(String(100), default="Manual paper", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_paper_orders_status_created", "status", "created_at"),)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

class Quote(Base):
    __tablename__ = "quotes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(8), default="NSE", nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="manual_paper_feed", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
