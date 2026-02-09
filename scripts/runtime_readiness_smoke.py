from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import httpx


def wait_for_health(url: str, timeout_s: int = 90) -> None:
    deadline = time.time() + timeout_s
    last_error = "unknown_error"
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url)
                if res.status_code == 200 and res.json().get("status") == "ok":
                    return
                last_error = f"bad_status_{res.status_code}"
        except Exception as exc:  # pragma: no cover - network/runtime branch
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"health_check_timeout: {url} ({last_error})")


def evaluate_model_status(status: dict[str, Any], require_ready: bool) -> list[str]:
    issues: list[str] = []
    mode = status.get("mode")
    enabled = status.get("enabled")
    ready = status.get("ready")

    if mode is None:
        issues.append("missing_mode")
    if enabled is None:
        issues.append("missing_enabled")
    if ready is None:
        issues.append("missing_ready")
    if require_ready and enabled is True and ready is not True:
        issues.append("enabled_but_not_ready")
    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live runtime readiness smoke check.")
    parser.add_argument("--agent-url", default="http://localhost:8002")
    parser.add_argument("--timeout-s", type=int, default=120)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("eval/results/runtime_readiness_smoke.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    agent_url = args.agent_url.rstrip("/")
    wait_for_health(f"{agent_url}/health", timeout_s=args.timeout_s)

    with httpx.Client(timeout=20.0) as client:
        model = client.get(f"{agent_url}/chat/model/status")
        model.raise_for_status()
        model_status = model.json()

        start = client.post(f"{agent_url}/chat/start", json={})
        start.raise_for_status()
        start_payload = start.json()

        resume = client.post(
            f"{agent_url}/chat/resume",
            json={"session_id": start_payload["session_id"]},
        )
        resume.raise_for_status()
        resume_payload = resume.json()

    issues = evaluate_model_status(model_status, require_ready=args.require_ready)
    if resume_payload.get("session_id") != start_payload.get("session_id"):
        issues.append("resume_session_mismatch")
    if not isinstance(resume_payload.get("messages"), list):
        issues.append("resume_messages_missing")

    report = {
        "ok": len(issues) == 0,
        "agent_url": agent_url,
        "model_status": model_status,
        "session_id": start_payload.get("session_id"),
        "case_id": start_payload.get("case_id"),
        "issues": issues,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "output": str(args.output)}, ensure_ascii=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
