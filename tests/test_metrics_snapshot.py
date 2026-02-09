from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_metrics_snapshot import render_markdown


def test_render_markdown_contains_sections():
    eval_report = {"metrics": {"n": 10, "decision_accuracy": 0.9}}
    conv_report = {"metrics": {"n": 3, "task_success_rate": 1.0}}
    safety_report = {"summary": {"total": 5, "passed": 5, "pass_rate": 1.0}}
    audit_report = {"ok": True, "warnings": []}
    model_status = {"mode": "hybrid", "enabled": True, "ready": True, "adapter_dir": "models/dpo_qlora/adapter"}
    md = render_markdown(eval_report, conv_report, safety_report, audit_report, model_status)
    assert "## Offline Eval (synthetic held-out)" in md
    assert "## Conversational Eval" in md
    assert "## Safety Suite" in md
    assert "## Final Audit" in md
    assert "## Model Runtime" in md
    assert "- decision_accuracy: 0.9" in md
