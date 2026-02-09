import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ship_ready_gate import check


def test_check_missing_files(tmp_path: Path):
    out = check(tmp_path, max_age_hours=1.0)
    assert out["ok"] is False
    assert out["present_count"] == 0
    assert len(out["missing"]) > 0


def test_check_flags_demo_semantic_issues(tmp_path: Path):
    files = [
        "docs/METRICS.md",
        "docs/MODEL_STATUS.md",
        "docs/PORTFOLIO_REPORT.md",
        "docs/RELEASE_SUMMARY.md",
        "docs/RELEASE_NOTES.md",
        "eval/results/eval_report.json",
        "eval/results/conversation_eval_report.json",
        "eval/results/safety_report.json",
        "eval/results/final_audit_report.json",
        "eval/results/model_runtime_status.json",
        "eval/results/model_handoff_report.json",
        "eval/results/demo_scenarios.json",
        "dist/release_manifest.json",
    ]
    for rel in files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".json":
            p.write_text("{}", encoding="utf-8")
        else:
            p.write_text("ok", encoding="utf-8")

    out = check(tmp_path, max_age_hours=24.0)
    assert out["ok"] is False
    assert out["content_issues"]
    assert any("demo_scenarios" in x for x in out["content_issues"])


def test_check_passes_with_required_demo_scenarios(tmp_path: Path):
    file_payloads = {
        "docs/METRICS.md": "ok",
        "docs/MODEL_STATUS.md": "ok",
        "docs/PORTFOLIO_REPORT.md": "ok",
        "docs/RELEASE_SUMMARY.md": "ok",
        "docs/RELEASE_NOTES.md": "ok",
        "eval/results/eval_report.json": "{}",
        "eval/results/conversation_eval_report.json": "{}",
        "eval/results/safety_report.json": "{}",
        "eval/results/final_audit_report.json": "{}",
        "eval/results/model_runtime_status.json": '{"mode":"hybrid","enabled":true,"ready":true,"missing_artifacts":[],"load_error":null}',
        "eval/results/model_handoff_report.json": '{"ok":true,"issues":[],"warnings":[]}',
        "dist/release_manifest.json": "{}",
    }
    for rel, content in file_payloads.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    demo = {
        "scenarios": [
            {"scenario": "damaged_evidence"},
            {"scenario": "escalation"},
            {"scenario": "cancel_processing"},
            {"scenario": "resume_session"},
        ]
    }
    demo_path = tmp_path / "eval/results/demo_scenarios.json"
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    demo_path.write_text(json.dumps(demo), encoding="utf-8")

    out = check(tmp_path, max_age_hours=24.0)
    assert out["ok"] is True
    assert out["content_issues"] == []


def test_check_flags_model_handoff_not_ok(tmp_path: Path):
    file_payloads = {
        "docs/METRICS.md": "ok",
        "docs/MODEL_STATUS.md": "ok",
        "docs/PORTFOLIO_REPORT.md": "ok",
        "docs/RELEASE_SUMMARY.md": "ok",
        "docs/RELEASE_NOTES.md": "ok",
        "eval/results/eval_report.json": "{}",
        "eval/results/conversation_eval_report.json": "{}",
        "eval/results/safety_report.json": "{}",
        "eval/results/final_audit_report.json": "{}",
        "eval/results/model_runtime_status.json": '{"mode":"hybrid","enabled":true,"ready":true,"missing_artifacts":[],"load_error":null}',
        "eval/results/model_handoff_report.json": '{"ok":false,"issues":["runtime_enabled_but_not_ready"]}',
        "dist/release_manifest.json": "{}",
    }
    for rel, content in file_payloads.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    demo = {
        "scenarios": [
            {"scenario": "damaged_evidence"},
            {"scenario": "escalation"},
            {"scenario": "cancel_processing"},
            {"scenario": "resume_session"},
        ]
    }
    demo_path = tmp_path / "eval/results/demo_scenarios.json"
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    demo_path.write_text(json.dumps(demo), encoding="utf-8")

    out = check(tmp_path, max_age_hours=24.0)
    assert out["ok"] is False
    assert "model_handoff_not_ok" in out["content_issues"]


def test_check_requires_runtime_smoke_when_flagged(tmp_path: Path):
    file_payloads = {
        "docs/METRICS.md": "ok",
        "docs/MODEL_STATUS.md": "ok",
        "docs/PORTFOLIO_REPORT.md": "ok",
        "docs/RELEASE_SUMMARY.md": "ok",
        "docs/RELEASE_NOTES.md": "ok",
        "eval/results/eval_report.json": "{}",
        "eval/results/conversation_eval_report.json": "{}",
        "eval/results/safety_report.json": "{}",
        "eval/results/final_audit_report.json": "{}",
        "eval/results/model_runtime_status.json": '{"mode":"hybrid","enabled":true,"ready":true,"missing_artifacts":[],"load_error":null}',
        "eval/results/model_handoff_report.json": '{"ok":true,"issues":[],"warnings":[]}',
        "dist/release_manifest.json": "{}",
    }
    for rel, content in file_payloads.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    demo = {
        "scenarios": [
            {"scenario": "damaged_evidence"},
            {"scenario": "escalation"},
            {"scenario": "cancel_processing"},
            {"scenario": "resume_session"},
        ]
    }
    demo_path = tmp_path / "eval/results/demo_scenarios.json"
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    demo_path.write_text(json.dumps(demo), encoding="utf-8")

    out = check(tmp_path, max_age_hours=24.0, require_runtime_smoke=True)
    assert out["ok"] is False
    assert "eval/results/runtime_readiness_smoke.json" in out["missing"]


def test_check_accepts_runtime_smoke_when_present(tmp_path: Path):
    file_payloads = {
        "docs/METRICS.md": "ok",
        "docs/MODEL_STATUS.md": "ok",
        "docs/PORTFOLIO_REPORT.md": "ok",
        "docs/RELEASE_SUMMARY.md": "ok",
        "docs/RELEASE_NOTES.md": "ok",
        "eval/results/eval_report.json": "{}",
        "eval/results/conversation_eval_report.json": "{}",
        "eval/results/safety_report.json": "{}",
        "eval/results/final_audit_report.json": "{}",
        "eval/results/model_runtime_status.json": '{"mode":"hybrid","enabled":true,"ready":true,"missing_artifacts":[],"load_error":null}',
        "eval/results/model_handoff_report.json": '{"ok":true,"issues":[],"warnings":[]}',
        "eval/results/runtime_readiness_smoke.json": '{"ok":true,"model_status":{"mode":"hybrid","enabled":true,"ready":true}}',
        "dist/release_manifest.json": "{}",
    }
    for rel, content in file_payloads.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    demo = {
        "scenarios": [
            {"scenario": "damaged_evidence"},
            {"scenario": "escalation"},
            {"scenario": "cancel_processing"},
            {"scenario": "resume_session"},
        ]
    }
    demo_path = tmp_path / "eval/results/demo_scenarios.json"
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    demo_path.write_text(json.dumps(demo), encoding="utf-8")

    out = check(tmp_path, max_age_hours=24.0, require_runtime_smoke=True)
    assert out["ok"] is True
    assert "eval/results/runtime_readiness_smoke.json" not in out["missing"]
