from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import services.agent_server.app.main as main_module


class _FakeFlow:
    def __init__(self, tools, llm=None):
        self.tools = tools
        self.llm = llm

    def resume(self, session_id: str):
        return {
            "session_id": session_id,
            "case_id": "CASE-RESUME-1",
            "assistant_message": "Select your order.",
            "status_chip": "Awaiting User Choice",
            "controls": [
                {
                    "control_type": "dropdown",
                    "field": "selected_order_id",
                    "label": "Select order",
                    "options": [{"label": "ORD-1001 (delivered)", "value": "ORD-1001"}],
                }
            ],
            "timeline": [{"time": "2026-02-09T00:00:00+00:00", "event": "Listed orders", "detail": "count=1"}],
            "messages": [{"role": "assistant", "content": "Select your order."}],
        }


def test_chat_resume_rejects_invalid_session_id():
    with TestClient(main_module.app) as client:
        response = client.post("/chat/resume", json={"session_id": "<SESSION_ID>"})
    assert response.status_code == 422


def test_chat_resume_success(monkeypatch):
    monkeypatch.setattr(main_module, "ChatFlowManager", _FakeFlow)
    with TestClient(main_module.app) as client:
        response = client.post("/chat/resume", json={"session_id": "SES-123"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "SES-123"
    assert body["status_chip"] == "Awaiting User Choice"
    assert body["messages"]
