import os
import sys
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Tests use a temporary SQLite database so the local demo database is not polluted.
tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
os.environ["DATABASE_URL"] = "sqlite:///" + tmp.name

# Modules may have been imported by a test runner plugin before env assignment.
# This file is intended to run in a fresh pytest process.
from app.main import app
client = TestClient(app)

def test_health_and_paper_only():
    r=client.get("/health")
    assert r.status_code==200
    assert r.json()["mode"]=="PAPER"
    assert r.json()["live_execution_enabled"] is False

def test_risk_settings_read():
    r=client.get("/api/v1/risk-settings")
    assert r.status_code==200
    assert r.json()["max_open_positions"]>=1

def test_create_order_and_idempotent_retry():
    payload={"instrument":"TESTABC","exchange":"NSE","side":"BUY","quantity":2,
             "entry_price":"100","stop_loss":"95","target_price":"110","strategy_name":"pytest"}
    headers={"Idempotency-Key":"pytest-order-key-0001"}
    r=client.post("/api/v1/paper/orders",json=payload,headers=headers)
    assert r.status_code==201, r.text
    order_id=r.json()["id"]
    r2=client.post("/api/v1/paper/orders",json=payload,headers=headers)
    assert r2.status_code==201
    assert r2.json()["id"]==order_id

def test_invalid_levels_rejected():
    payload={"instrument":"TESTXYZ","side":"BUY","quantity":1,
             "entry_price":"100","stop_loss":"105","target_price":"110"}
    r=client.post("/api/v1/paper/orders",json=payload,headers={"Idempotency-Key":"pytest-invalid-0001"})
    assert r.status_code==422

def test_quote_triggers_target_exit():
    payload={"instrument":"TARGETTEST","side":"BUY","quantity":1,
             "entry_price":"100","stop_loss":"95","target_price":"110"}
    r=client.post("/api/v1/paper/orders",json=payload,headers={"Idempotency-Key":"pytest-target-0001"})
    assert r.status_code==201, r.text
    order_id=r.json()["id"]
    q=client.post("/api/v1/paper/quotes",json={"instrument":"TARGETTEST","price":"112","is_synthetic":True})
    assert q.status_code==201
    assert order_id in q.json()["closed_order_ids"]
    o=client.get(f"/api/v1/orders/{order_id}")
    assert o.status_code==200
    assert o.json()["status"]=="CLOSED"
    assert o.json()["exit_reason"]=="TARGET"

def test_analytics_and_audit():
    assert client.get("/api/v1/analytics/performance").status_code==200
    assert client.get("/api/v1/audit-events").status_code==200

def test_idempotency_key_reuse_with_different_payload_rejected():
    payload={"instrument":"IDEMPOTENCYABC","side":"BUY","quantity":1,
             "entry_price":"100","stop_loss":"95","target_price":"110"}
    headers={"Idempotency-Key":"pytest-same-key-0001"}
    first=client.post("/api/v1/paper/orders",json=payload,headers=headers)
    assert first.status_code==201, first.text
    changed={**payload,"quantity":2}
    second=client.post("/api/v1/paper/orders",json=changed,headers=headers)
    assert second.status_code==409


def test_risk_settings_update_cannot_resume_halted_entries():
    halted=client.post("/api/v1/admin/kill-switch?halted=true")
    assert halted.status_code==200
    current=client.get("/api/v1/risk-settings").json()
    update={
        "max_capital":str(current["max_capital"]),
        "max_daily_loss":str(current["max_daily_loss"]),
        "max_risk_per_trade_pct":str(current["max_risk_per_trade_pct"]),
        "max_open_positions":current["max_open_positions"],
        "cash_reserve_pct":str(current["cash_reserve_pct"]),
        "halted":False,
    }
    saved=client.put("/api/v1/risk-settings",json=update)
    assert saved.status_code==200, saved.text
    assert saved.json()["halted"] is True
    assert client.get("/api/v1/system/status").json()["risk_halted"] is True
    client.post("/api/v1/admin/kill-switch?halted=false")


def test_latest_quote_is_exchange_specific():
    nse=client.post("/api/v1/paper/quotes",json={"instrument":"EXCHTEST","exchange":"NSE","price":"101"})
    bse=client.post("/api/v1/paper/quotes",json={"instrument":"EXCHTEST","exchange":"BSE","price":"102"})
    assert nse.status_code==201 and bse.status_code==201
    assert client.get("/api/v1/quotes/latest?instrument=EXCHTEST&exchange=NSE").json()["price"]==101
    assert client.get("/api/v1/quotes/latest?instrument=EXCHTEST&exchange=BSE").json()["price"]==102


def test_order_exit_is_not_repeatable():
    payload={"instrument":"EXITONCE","side":"BUY","quantity":1,
             "entry_price":"100","stop_loss":"95","target_price":"110"}
    created=client.post("/api/v1/paper/orders",json=payload,headers={"Idempotency-Key":"pytest-exit-once-0001"})
    assert created.status_code==201, created.text
    order_id=created.json()["id"]
    first=client.post(f"/api/v1/orders/{order_id}/exit",json={"exit_price":"105","reason":"MANUAL"})
    assert first.status_code==200, first.text
    second=client.post(f"/api/v1/orders/{order_id}/exit",json={"exit_price":"106","reason":"MANUAL"})
    assert second.status_code==409
