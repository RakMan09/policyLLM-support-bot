from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.stack_smoke import assert_resume_payload, choose_control


def test_choose_control_returns_first_value():
    payload = {
        "controls": [
            {
                "field": "selected_order_id",
                "options": [{"label": "ORD-1", "value": "ORD-1"}],
            }
        ]
    }
    assert choose_control(payload, "selected_order_id") == "ORD-1"


def test_assert_resume_payload_accepts_valid_payload():
    payload = {
        "session_id": "SES-1",
        "case_id": "CASE-1",
        "status_chip": "Awaiting User Choice",
        "messages": [{"role": "assistant", "content": "Select order"}],
    }
    assert_resume_payload(
        payload,
        session_id="SES-1",
        case_id="CASE-1",
        expected_status_chip="Awaiting User Choice",
    )
