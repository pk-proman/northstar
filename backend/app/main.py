from datetime import datetime, timezone, timedelta, date
from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import uuid4
import hashlib
import json
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import Base, engine, get_db
from . import models, schemas, services
from .config import TRADING_MODE, LIVE_EXECUTION_ENABLED

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from .database import SessionLocal
    db = SessionLocal()
    try:
        services.ensure_settings(db)
        db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title="Northstar Paper Trading API", version="1.1.0",
              description="Paper-trading backend. Live execution is deliberately not implemented.",
              lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "mode": "PAPER", "live_execution_enabled": False,
            "configured_mode": TRADING_MODE, "live_config_requested": LIVE_EXECUTION_ENABLED}

@app.get("/api/v1/portfolio/summary")
def portfolio_summary(db: Session = Depends(get_db)):
    settings = services.ensure_settings(db)
    db.commit()
    open_orders = services.open_positions(db)
    unrealized = services.open_unrealized(db)
    realized = services.realized_pnl(db)
    flows = services.external_flows(db)
    capital = flows + realized + unrealized
    gross_exposure = sum((o.entry_fill_price * o.quantity for o in open_orders), Decimal("0"))
    return {
        "mode": "PAPER", "currency": "INR",
        "external_flows": flows, "realized_pnl": realized, "unrealized_pnl": unrealized,
        "portfolio_value": capital, "open_positions": len(open_orders),
        "gross_open_exposure": gross_exposure, "available_risk_budget": max(Decimal("0"), settings.max_daily_loss-services.daily_realized_loss(db)),
        "risk_halted": settings.halted
    }

@app.get("/api/v1/capital-transactions")
def list_capital_transactions(db: Session = Depends(get_db)):
    rows = db.query(models.CapitalTransaction).order_by(models.CapitalTransaction.id.desc()).all()
    return [{"id":x.id,"transaction_type":x.transaction_type,"amount":x.amount,"reference":x.reference,
             "note":x.note,"effective_at":x.effective_at,"created_at":x.created_at} for x in rows]

@app.post("/api/v1/capital-transactions", status_code=201)
def create_capital_transaction(req: schemas.CapitalCreate, db: Session = Depends(get_db)):
    services.ensure_settings(db)
    if db.query(models.CapitalTransaction).filter_by(reference=req.reference).first():
        raise HTTPException(409, "Capital reference already exists.")
    flows = services.external_flows(db)
    settings = db.get(models.RiskSettings, 1)
    proposed = flows + (req.amount if req.transaction_type == "DEPOSIT" else -req.amount)
    if req.transaction_type == "WITHDRAWAL" and req.amount > flows:
        raise HTTPException(422, "Withdrawal exceeds recorded external capital balance.")
    if req.transaction_type == "DEPOSIT" and proposed > settings.max_capital:
        raise HTTPException(422, "Deposit would exceed configured capital limit.")
    row = models.CapitalTransaction(transaction_type=req.transaction_type, amount=req.amount,
                                    reference=req.reference, note=req.note)
    db.add(row); db.flush()
    services.audit(db, "CAPITAL_TRANSACTION_CREATED", "capital_transaction", row.id, "SUCCESS",
                   {"type":req.transaction_type,"amount":str(req.amount),"reference":req.reference})
    db.commit(); db.refresh(row)
    return {"id":row.id,"transaction_type":row.transaction_type,"amount":row.amount,"reference":row.reference}

@app.get("/api/v1/risk-settings")
def get_risk_settings(db: Session = Depends(get_db)):
    s = services.ensure_settings(db); db.commit()
    return {"max_capital":s.max_capital,"max_daily_loss":s.max_daily_loss,
            "max_risk_per_trade_pct":s.max_risk_per_trade_pct,"max_open_positions":s.max_open_positions,
            "cash_reserve_pct":s.cash_reserve_pct,"halted":s.halted,"updated_at":s.updated_at}

@app.put("/api/v1/risk-settings")
def update_risk_settings(req: schemas.RiskSettingsUpdate, db: Session = Depends(get_db)):
    s = services.ensure_settings(db)
    # Risk configuration is deliberately separate from the emergency-stop state.
    # Extra legacy `halted` fields from older clients are ignored by the schema.
    changes = req.model_dump()
    for k, v in changes.items():
        setattr(s, k, v)
    services.audit(db, "RISK_SETTINGS_UPDATED", "risk_settings", s.id, "SUCCESS", req.model_dump(mode="json"))
    db.commit()
    return {"status":"updated","halted":s.halted}

@app.post("/api/v1/admin/kill-switch")
def kill_switch(halted: bool = Query(True), db: Session = Depends(get_db)):
    s = services.ensure_settings(db); s.halted = halted
    services.audit(db, "KILL_SWITCH_CHANGED", "risk_settings", s.id, "SUCCESS", {"halted":halted})
    db.commit()
    return {"halted":s.halted,"mode":"PAPER","note":"Blocks new paper entries; existing positions remain open unless their exit conditions trigger."}

@app.post("/api/v1/paper/orders", response_model=schemas.OrderOut, status_code=201)
def create_paper_order(req: schemas.PaperOrderCreate,
                       idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120),
                       db: Session = Depends(get_db)):
    # Explicit hard guard: this release exposes no live order endpoint.
    if TRADING_MODE != "PAPER" or LIVE_EXECUTION_ENABLED:
        raise HTTPException(503, "Unsafe mode configuration; paper order endpoint is disabled.")
    canonical_payload = req.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    # New requests have a durable fingerprint record. Legacy orders created before
    # this table existed are compared field-by-field for backward compatibility.
    record = db.query(models.IdempotencyRecord).filter_by(idempotency_key=idempotency_key).first()
    if record:
        if record.request_fingerprint != fingerprint:
            raise HTTPException(409, "Idempotency-Key was already used with a different order payload.")
        existing = db.get(models.PaperOrder, record.order_id)
        if existing is None:
            raise HTTPException(409, "Idempotency record exists but its paper order is missing; contact an administrator.")
        return existing

    existing = db.query(models.PaperOrder).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        same_request = (
            existing.instrument == req.instrument.upper()
            and existing.exchange == req.exchange
            and existing.side == req.side
            and existing.quantity == req.quantity
            and existing.requested_price == req.entry_price
            and existing.stop_loss == req.stop_loss
            and existing.target_price == req.target_price
            and existing.strategy_name == req.strategy_name
        )
        if not same_request:
            raise HTTPException(409, "Idempotency-Key was already used with a different order payload.")
        return existing

    approved, reasons, planned_loss = services.authorize_order(db, req)
    decision = {"approved":approved,"reasons":reasons,"planned_loss":str(planned_loss)}
    services.audit(db, "PAPER_ORDER_RISK_DECISION", "paper_order", idempotency_key,
                   "APPROVED" if approved else "REJECTED", decision)
    if not approved:
        db.commit()
        raise HTTPException(422, {"message":"Paper order rejected by risk controls.","reason_codes":reasons,"planned_loss":str(planned_loss)})
    fill = services.simulated_fill(req.entry_price, req.side)
    entry_fee = services.fee_for(fill * req.quantity)
    order = models.PaperOrder(
        client_order_ref=f"PAPER-{uuid4().hex[:16].upper()}",
        idempotency_key=idempotency_key, instrument=req.instrument.upper(), exchange=req.exchange,
        side=req.side, order_type="MARKET", quantity=req.quantity, requested_price=req.entry_price,
        stop_loss=req.stop_loss, target_price=req.target_price, status="OPEN",
        entry_fill_price=fill, mark_price=fill, fees=entry_fee, gross_pnl=Decimal("0"),
        net_pnl=-entry_fee, strategy_name=req.strategy_name
    )
    db.add(order)
    try:
        db.flush()
        db.add(models.IdempotencyRecord(
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            order_id=order.id,
        ))
        services.audit(db, "PAPER_ORDER_CREATED", "paper_order", order.id, "SUCCESS",
                       {"instrument":order.instrument,"side":order.side,"quantity":order.quantity,
                        "requested_price":str(req.entry_price),"simulated_fill":str(fill),"fees":str(entry_fee)})
        db.commit()
        db.refresh(order)
        return order
    except IntegrityError:
        # A concurrent request may have won the unique-key race. Roll back this
        # transaction, then return the winner only if its payload is identical.
        db.rollback()
        record = db.query(models.IdempotencyRecord).filter_by(idempotency_key=idempotency_key).first()
        if record:
            if record.request_fingerprint != fingerprint:
                raise HTTPException(409, "Idempotency-Key was already used with a different order payload.")
            winner = db.get(models.PaperOrder, record.order_id)
            if winner is not None:
                return winner
        existing = db.query(models.PaperOrder).filter_by(idempotency_key=idempotency_key).first()
        if existing:
            same_request = (
                existing.instrument == req.instrument.upper()
                and existing.exchange == req.exchange
                and existing.side == req.side
                and existing.quantity == req.quantity
                and existing.requested_price == req.entry_price
                and existing.stop_loss == req.stop_loss
                and existing.target_price == req.target_price
                and existing.strategy_name == req.strategy_name
            )
            if same_request:
                return existing
            raise HTTPException(409, "Idempotency-Key was already used with a different order payload.")
        raise

@app.get("/api/v1/orders", response_model=list[schemas.OrderOut])
def list_orders(status: str | None = None, instrument: str | None = None,
                limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    q = db.query(models.PaperOrder)
    if status:
        if status.upper() not in {"OPEN","CLOSED"}: raise HTTPException(422, "status must be OPEN or CLOSED")
        q=q.filter(models.PaperOrder.status==status.upper())
    if instrument: q=q.filter(models.PaperOrder.instrument==instrument.upper())
    return q.order_by(models.PaperOrder.created_at.desc()).limit(limit).all()

@app.get("/api/v1/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    row=db.get(models.PaperOrder,order_id)
    if not row: raise HTTPException(404,"Order not found")
    return row

@app.post("/api/v1/orders/{order_id}/exit", response_model=schemas.OrderOut)
def exit_order(order_id: int, req: schemas.ManualExit, db: Session = Depends(get_db)):
    row=(db.query(models.PaperOrder)
         .filter(models.PaperOrder.id == order_id)
         .with_for_update()
         .first())
    if not row: raise HTTPException(404,"Order not found")
    if row.status != "OPEN": raise HTTPException(409,"Only open paper orders can be exited")
    services.mark_order(db,row,req.exit_price,req.reason)
    db.commit(); db.refresh(row)
    return row

@app.post("/api/v1/paper/quotes", status_code=201)
def ingest_paper_quote(req: schemas.QuoteCreate, db: Session = Depends(get_db)):
    # This endpoint is for test/manual paper quote injection only. It is not a market feed.
    quote = models.Quote(instrument=req.instrument.upper(),exchange=req.exchange,price=req.price,
                         source=req.source,observed_at=req.observed_at or datetime.now(timezone.utc),
                         is_synthetic=req.is_synthetic)
    db.add(quote); db.flush()
    closed_ids=services.process_quote(db,quote)
    services.audit(db,"PAPER_QUOTE_PROCESSED","quote",quote.id,"SUCCESS",
                   {"instrument":quote.instrument,"price":str(quote.price),"closed_order_ids":closed_ids,
                    "synthetic":quote.is_synthetic})
    db.commit()
    return {"quote_id":quote.id,"instrument":quote.instrument,"price":quote.price,
            "closed_order_ids":closed_ids,"note":"Manual/synthetic paper quote; no live market data connection."}

@app.get("/api/v1/analytics/performance")
def performance(from_date: date | None = Query(None, alias="from"),
                to_date: date | None = Query(None, alias="to"),
                strategy: str | None = None, instrument: str | None = None,
                db: Session = Depends(get_db)):
    q=db.query(models.PaperOrder).filter(models.PaperOrder.status=="CLOSED")
    if from_date: q=q.filter(models.PaperOrder.closed_at >= datetime(from_date.year,from_date.month,from_date.day,tzinfo=timezone.utc))
    if to_date: q=q.filter(models.PaperOrder.closed_at < datetime(to_date.year,to_date.month,to_date.day,tzinfo=timezone.utc)+timedelta(days=1))
    if strategy: q=q.filter(models.PaperOrder.strategy_name==strategy)
    if instrument: q=q.filter(models.PaperOrder.instrument==instrument.upper())
    rows=q.all()
    wins=[o for o in rows if o.net_pnl>0]; losses=[o for o in rows if o.net_pnl<0]
    gross_win=sum((o.net_pnl for o in wins),Decimal("0"))
    gross_loss=abs(sum((o.net_pnl for o in losses),Decimal("0")))
    net=sum((o.net_pnl for o in rows),Decimal("0"))
    fees=sum((o.fees for o in rows),Decimal("0"))
    return {"from":from_date,"to":to_date,"trade_count":len(rows),"wins":len(wins),
            "losses":len(losses),"win_rate_pct":(Decimal(len(wins))*100/len(rows) if rows else None),
            "profit_factor":(gross_win/gross_loss if gross_loss else (None if not gross_win else "INF")),
            "net_realized_pnl":net,"total_fees":fees,
            "trades":[{"id":o.id,"instrument":o.instrument,"strategy_name":o.strategy_name,
                       "side":o.side,"quantity":o.quantity,"entry_fill_price":o.entry_fill_price,
                       "exit_fill_price":o.exit_fill_price,"fees":o.fees,"net_pnl":o.net_pnl,
                       "exit_reason":o.exit_reason,"closed_at":o.closed_at} for o in rows]}

@app.get("/api/v1/audit-events")
def list_audit_events(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    rows=db.query(models.AuditEvent).order_by(models.AuditEvent.created_at.desc()).limit(limit).all()
    return [{"id":r.id,"event_type":r.event_type,"entity_type":r.entity_type,"entity_id":r.entity_id,
             "outcome":r.outcome,"details":r.details,"created_at":r.created_at} for r in rows]

@app.get("/api/v1/quotes/latest")
def latest_quote(instrument: str, exchange: str = Query("NSE", pattern="^(NSE|BSE)$"), db: Session = Depends(get_db)):
    q=db.query(models.Quote).filter_by(instrument=instrument.upper(), exchange=exchange).order_by(models.Quote.observed_at.desc()).first()
    if not q: raise HTTPException(404,"No paper quote recorded for this instrument.")
    return {"instrument":q.instrument,"exchange":q.exchange,"price":q.price,"source":q.source,
            "observed_at":q.observed_at,"is_synthetic":q.is_synthetic}

@app.get("/api/v1/system/status")
def system_status(db: Session = Depends(get_db)):
    s=services.ensure_settings(db)
    open_count=db.query(models.PaperOrder).filter_by(status="OPEN").count()
    quote_count=db.query(models.Quote).count()
    audit_count=db.query(models.AuditEvent).count()
    db.commit()
    return {"mode":"PAPER","live_execution":False,"risk_halted":s.halted,
            "open_paper_orders":open_count,"quotes_ingested":quote_count,"audit_events":audit_count,
            "broker_connected":False,"market_data_connected":False}
