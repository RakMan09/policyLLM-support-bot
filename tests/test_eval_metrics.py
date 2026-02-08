from pathlib import Path
import sys
import types

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sys.modules.setdefault("httpx", types.SimpleNamespace(Client=None))

from eval.eval_harness import aggregate, evaluate_case, is_subsequence


def test_is_subsequence():
    assert is_subsequence(["a", "b"], ["a", "x", "b"])
    assert not is_subsequence(["a", "b", "c"], ["a", "c", "b"])


def test_evaluate_case_decision_and_tools():
    case = {"case_id": "c1", "policy_decision": {"next_action": "deny"}}
    pred = {
        "final_action": "deny",
        "tool_trace": [
            {"tool_name": "lookup_order"},
            {"tool_name": "get_policy"},
            {"tool_name": "check_eligibility"},
            {"tool_name": "compute_refund"},
        ],
    }
    out = evaluate_case(case, pred)
    assert out["decision_correct"] is True
    assert out["valid_tools"] is True
    assert out["sequence_ok"] is True


def test_aggregate_metrics():
    rows = [
        {
            "decision_correct": True,
            "valid_tools": True,
            "sequence_ok": True,
            "efficient": True,
            "efficiency_calls": 4,
        },
        {
            "decision_correct": False,
            "valid_tools": True,
            "sequence_ok": False,
            "efficient": False,
            "efficiency_calls": 7,
        },
    ]
    metrics = aggregate(rows)
    assert metrics["n"] == 2
    assert metrics["decision_accuracy"] == 0.5
    assert metrics["tool_validity_rate"] == 1.0
    assert metrics["sequence_correct_rate"] == 0.5
