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
