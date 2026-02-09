from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.verify_model_handoff import evaluate


def test_evaluate_passes_for_ready_hybrid_runtime():
    report = evaluate(
        {
            "mode": "hybrid",
            "enabled": True,
            "ready": True,
            "missing_artifacts": [],
            "load_error": None,
        }
    )
    assert report["ok"] is True
    assert report["issues"] == []


def test_evaluate_fails_when_enabled_but_not_ready():
    report = evaluate(
        {
            "mode": "hybrid",
            "enabled": True,
            "ready": False,
            "missing_artifacts": ["models/dpo_qlora/adapter/adapter_model.safetensors"],
            "load_error": None,
        }
    )
    assert report["ok"] is False
    assert "runtime_enabled_but_not_ready" in report["issues"]
    assert "adapter_artifacts_missing" in report["issues"]
