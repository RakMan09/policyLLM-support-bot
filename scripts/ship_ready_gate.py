from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FILES = [
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


def _hours_old(path: Path) -> float:
    now = datetime.now(timezone.utc).timestamp()
    return max(0.0, (now - path.stat().st_mtime) / 3600.0)


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _validate_demo_scenarios(path: Path) -> list[str]:
    payload = _load_json(path)
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        return ["demo_scenarios_invalid_format"]
    names = {item.get("scenario") for item in scenarios if isinstance(item, dict)}
    required = {"damaged_evidence", "escalation", "cancel_processing", "resume_session"}
    missing = sorted(required - names)
    issues: list[str] = []
    if len(scenarios) < 4:
        issues.append("demo_scenarios_too_few")
    if missing:
        issues.append(f"demo_scenarios_missing:{','.join(missing)}")
    return issues


def _validate_model_runtime(path: Path) -> list[str]:
    payload = _load_json(path)
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["model_runtime_invalid_format"]
    if "ready" not in payload:
        issues.append("model_runtime_missing_ready")
    if "mode" not in payload:
        issues.append("model_runtime_missing_mode")
    if "enabled" not in payload:
        issues.append("model_runtime_missing_enabled")
    return issues


def _validate_model_handoff(path: Path) -> list[str]:
    payload = _load_json(path)
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["model_handoff_invalid_format"]
    if payload.get("ok") is not True:
        issues.append("model_handoff_not_ok")
    if "issues" not in payload:
        issues.append("model_handoff_missing_issues")
    return issues


def _validate_runtime_smoke(path: Path) -> list[str]:
    payload = _load_json(path)
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["runtime_smoke_invalid_format"]
    if payload.get("ok") is not True:
        issues.append("runtime_smoke_not_ok")
    if "model_status" not in payload:
        issues.append("runtime_smoke_missing_model_status")
    return issues


def check(repo_root: Path, max_age_hours: float, require_runtime_smoke: bool = False) -> dict:
    missing: list[str] = []
    stale: list[dict[str, float]] = []
    present: list[str] = []
    content_issues: list[str] = []

    for rel in REQUIRED_FILES:
        p = repo_root / rel
        if not p.exists():
            missing.append(rel)
            continue
        present.append(rel)
        age = _hours_old(p)
        if age > max_age_hours:
            stale.append({"path": rel, "hours_old": round(age, 2)})

    runtime_smoke_rel = "eval/results/runtime_readiness_smoke.json"
    runtime_smoke_path = repo_root / runtime_smoke_rel
    if require_runtime_smoke and not runtime_smoke_path.exists():
        missing.append(runtime_smoke_rel)
    if runtime_smoke_path.exists() and runtime_smoke_rel not in present:
        present.append(runtime_smoke_rel)
        age = _hours_old(runtime_smoke_path)
        if age > max_age_hours:
            stale.append({"path": runtime_smoke_rel, "hours_old": round(age, 2)})

    demo_path = repo_root / "eval/results/demo_scenarios.json"
    if demo_path.exists():
        content_issues.extend(_validate_demo_scenarios(demo_path))
    runtime_path = repo_root / "eval/results/model_runtime_status.json"
    if runtime_path.exists():
        content_issues.extend(_validate_model_runtime(runtime_path))
    handoff_path = repo_root / "eval/results/model_handoff_report.json"
    if handoff_path.exists():
        content_issues.extend(_validate_model_handoff(handoff_path))
    if runtime_smoke_path.exists():
        content_issues.extend(_validate_runtime_smoke(runtime_smoke_path))

    ok = not missing and not stale and not content_issues
    required_count = len(REQUIRED_FILES) + (1 if require_runtime_smoke else 0)
    return {
        "ok": ok,
        "required_count": required_count,
        "present_count": len(present),
        "missing": missing,
        "stale": stale,
        "content_issues": content_issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ship-ready gate for final release.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--max-age-hours", type=float, default=168.0)
    parser.add_argument("--require-runtime-smoke", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("eval/results/ship_ready_gate.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = check(args.repo_root.resolve(), args.max_age_hours, require_runtime_smoke=args.require_runtime_smoke)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "output": str(args.output)}, ensure_ascii=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
