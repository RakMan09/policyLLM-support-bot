from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.runtime_readiness_smoke import evaluate_model_status


def test_evaluate_model_status_passes_ready_enabled():
    issues = evaluate_model_status(
        {"mode": "hybrid", "enabled": True, "ready": True},
        require_ready=True,
    )
    assert issues == []


def test_evaluate_model_status_flags_enabled_not_ready_when_required():
    issues = evaluate_model_status(
        {"mode": "hybrid", "enabled": True, "ready": False},
        require_ready=True,
    )
    assert "enabled_but_not_ready" in issues
