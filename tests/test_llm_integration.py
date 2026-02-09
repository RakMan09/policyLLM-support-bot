from services.agent_server.app.chat_flow import ChatFlowManager
from services.agent_server.app.orchestrator import AgentOrchestrator
from services.agent_server.app.schemas import AgentRequest, ChatMessageRequest, ChatStartRequest


class FakeLLM:
    def __init__(self, *, reason: str | None = None, reply: str | None = None):
        self._reason = reason
        self._reply = reply

    def extract_reason(self, text: str, allowed_reasons: list[str]) -> str | None:
        if self._reason in allowed_reasons:
            return self._reason
        return None

    def draft_reply(self, objective: str, context: dict) -> str | None:
        return self._reply


class FakeTools:
    def __init__(self):
        self.sessions: dict[str, dict] = {}

    def create_session(self, payload):
        self.sessions[payload["session_id"]] = {
            "session_id": payload["session_id"],
            "case_id": payload["case_id"],
            "state": payload["state"],
            "status": payload["status"],
        }
        return self.sessions[payload["session_id"]]

    def get_session(self, payload):
        return self.sessions[payload["session_id"]]

    def update_session_state(self, payload):
        session = self.sessions[payload["session_id"]]
        session["state"].update(payload["state_patch"])
        if payload.get("status"):
            session["status"] = payload["status"]
        return session

    def append_chat_message(self, payload):
        return {"ok": True}

    def list_orders(self, payload):
        return {"orders": [{"order_id": "ORD-1001", "status": "delivered"}]}

    def list_order_items(self, payload):
        return {"items": [{"item_id": "ITEM-1", "item_category": "electronics"}]}

    def set_selected_order(self, payload):
        return {"ok": True}

    def set_selected_items(self, payload):
        return {"ok": True}

    def lookup_order(self, payload):
        return {
            "found": True,
            "order": {
                "order_id": "ORD-1001",
                "merchant_id": "M-001",
                "customer_email_masked": "al***@example.com",
                "customer_phone_last4": "1234",
                "item_id": "ITEM-1",
                "item_category": "electronics",
                "order_date": "2025-12-01",
                "delivery_date": "2025-12-05",
                "item_price": "120.00",
                "shipping_fee": "10.00",
                "status": "delivered",
            },
        }

    def get_policy(self, payload):
        return {
            "return_window_days": 15,
            "refund_shipping": True,
            "requires_evidence_for": ["damaged", "defective", "wrong_item"],
            "non_returnable_categories": ["perishable", "personal_care"],
        }

    def check_eligibility(self, payload):
        return {
            "eligible": True,
            "missing_info": [],
            "required_evidence": [],
            "decision_reason": "Eligible under policy",
        }

    def compute_refund(self, payload):
        return {
            "amount": "130.00",
            "breakdown": {"item": "120.00", "shipping": "10.00"},
            "refund_type": "full",
        }

    def create_return(self, payload):
        return {"rma_id": "RMA-1"}

    def create_label(self, payload):
        return {"label_id": "LBL-1", "url": "https://labels.local/LBL-1.pdf"}

    def create_escalation(self, payload):
        return {"ticket_id": "ESC-1"}

    def create_replacement(self, payload):
        return {"replacement_id": "REP-1"}


def test_chat_flow_uses_llm_for_reason_extraction():
    tools = FakeTools()
    llm = FakeLLM(reason="damaged")
    flow = ChatFlowManager(tools, llm=llm)
    start = flow.start(ChatStartRequest(customer_identifier="alice@example.com"))

    flow.message(ChatMessageRequest(session_id=start.session_id, text="", selected_order_id="ORD-1001"))
    flow.message(ChatMessageRequest(session_id=start.session_id, text="", selected_item_ids=["ITEM-1"]))
    out = flow.message(ChatMessageRequest(session_id=start.session_id, text="issue with my item"))
    assert out.status_chip == "Awaiting User Choice"
    assert any(c.field == "preferred_resolution" for c in out.controls)


def test_orchestrator_uses_llm_reply_draft():
    tools = FakeTools()
    llm = FakeLLM(reply="Drafted approval reply")
    orchestrator = AgentOrchestrator(tools, llm=llm)

    response = orchestrator.run(
        AgentRequest(
            case_id="CASE-1",
            customer_message="wrong item received",
            order_id="ORD-1001",
        )
    )
    assert response.final_action == "approve_return_and_refund"
    assert response.customer_reply == "Drafted approval reply"
