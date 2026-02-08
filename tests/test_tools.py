import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

db_path = Path("/tmp/refund_agent_test.db")
if db_path.exists():
    db_path.unlink()
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
from services.tool_server.app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_lookup_order_found(client: TestClient):
    response = client.post("/tools/lookup_order", json={"order_id": "ORD-1001"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["found"] is True
    assert payload["order"]["customer_email_masked"].startswith("al")


def test_create_return_idempotent(client: TestClient):
    body = {"order_id": "ORD-1001", "item_id": "ITEM-1", "method": "dropoff"}
    r1 = client.post("/tools/create_return", json=body)
    r2 = client.post("/tools/create_return", json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["rma_id"] == r2.json()["rma_id"]
