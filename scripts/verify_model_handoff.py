from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(snapshot: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    mode = str(snapshot.get("mode", "unknown"))
    enabled = bool(snapshot.get("enabled", False))
    ready = bool(snapshot.get("ready", False))
    missing = snapshot.get("missing_artifacts", [])
    load_error = snapshot.get("load_error")

    if enabled and mode in {"hybrid", "llm"} and not ready:
        issues.append("runtime_enabled_but_not_ready")
    if isinstance(missing, list) and missing:
        issues.append("adapter_artifacts_missing")
    if mode == "llm" and load_error:
        issues.append("llm_mode_load_error_present")
    if mode == "hybrid" and load_error:
        warnings.append("hybrid_mode_load_error_present")

    ok = len(issues) == 0
    return {
        "ok": ok,
        "mode": mode,
        "enabled": enabled,
        "ready": ready,
        "issues": issues,
        "warnings": warnings,
        "missing_artifacts": missing if isinstance(missing, list) else [],
        "load_error": load_error,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify model handoff readiness from runtime snapshot.")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("eval/results/model_runtime_status.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/model_handoff_report.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = evaluate(load_json(args.snapshot))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "output": str(args.output)}, ensure_ascii=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
