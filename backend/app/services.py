import json
from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from . import models
from .config import (
    INITIAL_CAPITAL_INR, MAX_CAPITAL_INR, MAX_DAILY_LOSS_INR,
    MAX_RISK_PER_TRADE_PCT, MAX_OPEN_POSITIONS, CASH_RESERVE_PCT,
    PAPER_FEE_RATE, PAPER_SLIPPAGE_BPS, TRADING_MODE, LIVE_EXECUTION_ENABLED
)

CENT = Decimal("0.01")
def money(x: Decimal) -> Decimal:
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)

def audit(db: Session, event_type: str, entity_type: str, entity_id: str, outcome: str, details: dict):
    db.add(models.AuditEvent(event_type=event_type, entity_type=entity_type, entity_id=str(entity_id),
                             outcome=outcome, details=json.dumps(details, default=str, sort_keys=True)))

def ensure_settings(db: Session) -> models.RiskSettings:
    settings = db.get(models.RiskSettings, 1)
    if settings is None:
        settings = models.RiskSettings(
            id=1, max_capital=MAX_CAPITAL_INR, max_daily_loss=MAX_DAILY_LOSS_INR,
            max_risk_per_trade_pct=MAX_RISK_PER_TRADE_PCT,
            max_open_positions=MAX_OPEN_POSITIONS, cash_reserve_pct=CASH_RESERVE_PCT, halted=False
        )
        db.add(settings)
        db.flush()
    if not db.query(models.CapitalTransaction).filter_by(reference="SYSTEM-INITIAL-CAPITAL").first():
        db.add(models.CapitalTransaction(
            transaction_type="DEPOSIT", amount=INITIAL_CAPITAL_INR,
            reference="SYSTEM-INITIAL-CAPITAL", note="Initial paper portfolio seed"
        ))
        db.flush()
    return settings

def external_flows(db: Session) -> Decimal:
    rows = db.query(models.CapitalTransaction).all()
    return sum((x.amount if x.transaction_type == "DEPOSIT" else -x.amount for x in rows), Decimal("0"))

def realized_pnl(db: Session, start: datetime | None = None, end: datetime | None = None) -> Decimal:
    q = db.query(func.coalesce(func.sum(models.PaperOrder.net_pnl), 0)).filter(models.PaperOrder.status == "CLOSED")
    if start: q = q.filter(models.PaperOrder.closed_at >= start)
    if end: q = q.filter(models.PaperOrder.closed_at < end)
    return Decimal(str(q.scalar() or 0))

def open_positions(db: Session):
    return db.query(models.PaperOrder).filter(models.PaperOrder.status == "OPEN").all()

def open_unrealized(db: Session) -> Decimal:
    total = Decimal("0")
    for p in open_positions(db):
        gross = (p.mark_price - p.entry_fill_price) * p.quantity
        if p.side == "SELL": gross = -gross
        total += gross - p.fees
    return money(total)

def capital_balance(db: Session) -> Decimal:
    return external_flows(db) + realized_pnl(db) + open_unrealized(db)

def daily_realized_loss(db: Session) -> Decimal:
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    pnl = realized_pnl(db, start=start)
    # A negative number means loss. Include current open losses conservatively.
    open_pnl = open_unrealized(db)
    combined = pnl + min(open_pnl, Decimal("0"))
    return max(Decimal("0"), -combined)

def authorize_order(db: Session, req) -> tuple[bool, list[str], Decimal]:
    # Serialize risk evaluation against the singleton settings row. On PostgreSQL,
    # concurrent order requests wait here and re-evaluate exposure after the prior
    # transaction commits. SQLite ignores FOR UPDATE (used only for local tests).
    ensure_settings(db)
    settings = (db.query(models.RiskSettings)
                .filter(models.RiskSettings.id == 1)
                .with_for_update()
                .one())
    reasons = []
    if TRADING_MODE != "PAPER" or LIVE_EXECUTION_ENABLED:
        reasons.append("UNSAFE_MODE_CONFIGURATION")
    if settings.halted:
        reasons.append("TRADING_HALTED")
    planned_loss = money(abs(req.entry_price - req.stop_loss) * req.quantity)
    max_risk = money(settings.max_capital * settings.max_risk_per_trade_pct / Decimal("100"))
    if planned_loss > max_risk:
        reasons.append("PER_TRADE_RISK_LIMIT")
    open_now = open_positions(db)
    if len(open_now) >= settings.max_open_positions:
        reasons.append("MAX_OPEN_POSITIONS")
    if any(p.instrument == req.instrument and p.side == req.side for p in open_now):
        reasons.append("DUPLICATE_ACTIVE_INSTRUMENT_DIRECTION")
    current_capital = capital_balance(db)
    max_deployable = settings.max_capital * (Decimal("1") - settings.cash_reserve_pct / Decimal("100"))
    gross_open_exposure = sum((p.entry_fill_price * p.quantity for p in open_now), Decimal("0"))
    if gross_open_exposure + req.entry_price * req.quantity > max_deployable:
        reasons.append("DEPLOYABLE_CAPITAL_LIMIT")
    if current_capital > settings.max_capital:
        reasons.append("MAX_CAPITAL_LIMIT")
    if daily_realized_loss(db) >= settings.max_daily_loss:
        reasons.append("DAILY_LOSS_LIMIT")
    return not reasons, reasons, planned_loss

def simulated_fill(entry: Decimal, side: str) -> Decimal:
    slip = PAPER_SLIPPAGE_BPS / Decimal("10000")
    # Conservative entry: pay more for buys, receive less for sells.
    return entry * (Decimal("1") + slip if side == "BUY" else Decimal("1") - slip)

def fee_for(notional: Decimal) -> Decimal:
    return money(abs(notional) * PAPER_FEE_RATE)

def mark_order(db: Session, order: models.PaperOrder, price: Decimal, reason: str | None = None):
    order.mark_price = price
    gross = (price - order.entry_fill_price) * order.quantity
    if order.side == "SELL": gross = -gross
    order.gross_pnl = money(gross)
    if reason:
        exit_fill = price * (Decimal("1") - PAPER_SLIPPAGE_BPS/Decimal("10000") if order.side == "BUY" else Decimal("1") + PAPER_SLIPPAGE_BPS/Decimal("10000"))
        exit_fee = fee_for(exit_fill * order.quantity)
        order.exit_fill_price = exit_fill
        order.fees = money(order.fees + exit_fee)
        realized = (exit_fill - order.entry_fill_price) * order.quantity
        if order.side == "SELL": realized = -realized
        order.gross_pnl = money(realized)
        order.net_pnl = money(realized - order.fees)
        order.status = "CLOSED"
        order.exit_reason = reason
        order.closed_at = datetime.now(timezone.utc)
        audit(db, "PAPER_ORDER_CLOSED", "paper_order", order.id, "SUCCESS", {
            "exit_reason": reason, "exit_fill_price": str(exit_fill), "gross_pnl": str(order.gross_pnl),
            "fees": str(order.fees), "net_pnl": str(order.net_pnl)
        })
    else:
        order.net_pnl = money(order.gross_pnl - order.fees)

def process_quote(db: Session, quote: models.Quote):
    orders = db.query(models.PaperOrder).filter_by(instrument=quote.instrument, exchange=quote.exchange, status="OPEN").all()
    closed = []
    for order in orders:
        px = quote.price
        mark_order(db, order, px)
        reason = None
        if order.side == "BUY":
            if px <= order.stop_loss: reason = "STOP_LOSS"
            elif px >= order.target_price: reason = "TARGET"
        else:
            if px >= order.stop_loss: reason = "STOP_LOSS"
            elif px <= order.target_price: reason = "TARGET"
        if reason:
            mark_order(db, order, px, reason)
            closed.append(order.id)
    return closed
