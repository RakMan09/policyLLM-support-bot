from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

ALLOWED_TOOLS = {
    "lookup_order",
    "get_policy",
    "check_eligibility",
    "compute_refund",
    "create_return",
    "create_label",
    "create_escalation",
}

READ_SEQUENCE = ["lookup_order", "get_policy", "check_eligibility", "compute_refund"]


def load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def call_agent(agent_url: str, case: dict[str, Any], timeout_s: float = 20.0) -> dict[str, Any]:
    payload = {
        "case_id": case["case_id"],
        "customer_message": case["customer_message"],
        "order_id": case.get("extracted_fields", {}).get("order_id"),
        "reason": case.get("issue_type"),
    }
    with httpx.Client(timeout=timeout_s) as client:
        response = client.post(f"{agent_url.rstrip('/')}/agent/respond", json=payload)
        response.raise_for_status()
        return response.json()


def tool_names(trace: list[dict[str, Any]]) -> list[str]:
    return [t.get("tool_name", "") for t in trace]


def is_subsequence(needles: list[str], haystack: list[str]) -> bool:
    i = 0
    for item in haystack:
        if i < len(needles) and item == needles[i]:
            i += 1
    return i == len(needles)


def evaluate_case(case: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    gold_action = case.get("policy_decision", {}).get("next_action")
    pred_action = pred.get("final_action")
    trace = pred.get("tool_trace", [])
    names = tool_names(trace)

    decision_correct = pred_action == gold_action

    valid_tools = all(name in ALLOWED_TOOLS for name in names)

    seq_ok = True
    if pred_action in {"deny", "request_info", "approve_refund", "approve_return_and_refund"}:
        seq_ok = is_subsequence(READ_SEQUENCE, names)

    efficiency_calls = len(names)
    expected_max = 6 if pred_action == "approve_return_and_refund" else 4
    efficient = efficiency_calls <= expected_max

    return {
        "case_id": case["case_id"],
        "gold_action": gold_action,
        "pred_action": pred_action,
        "decision_correct": decision_correct,
        "valid_tools": valid_tools,
        "sequence_ok": seq_ok,
        "efficiency_calls": efficiency_calls,
        "efficient": efficient,
        "tool_names": names,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "decision_accuracy": 0.0,
            "tool_validity_rate": 0.0,
            "sequence_correct_rate": 0.0,
            "efficiency_rate": 0.0,
            "avg_calls_per_episode": 0.0,
        }

    n = len(rows)
    decision_accuracy = sum(1 for r in rows if r["decision_correct"]) / n
    tool_validity_rate = sum(1 for r in rows if r["valid_tools"]) / n
    sequence_correct_rate = sum(1 for r in rows if r["sequence_ok"]) / n
    efficiency_rate = sum(1 for r in rows if r["efficient"]) / n
    avg_calls = mean(r["efficiency_calls"] for r in rows)

    return {
        "n": n,
        "decision_accuracy": round(decision_accuracy, 4),
        "tool_validity_rate": round(tool_validity_rate, 4),
        "sequence_correct_rate": round(sequence_correct_rate, 4),
        "efficiency_rate": round(efficiency_rate, 4),
        "avg_calls_per_episode": round(avg_calls, 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline evaluation harness for refund-returns agent")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/processed/synthetic_cases_test.jsonl"),
        help="Held-out synthetic test set path.",
    )
    parser.add_argument("--agent-url", default="http://localhost:8002")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("eval/results/eval_report.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_jsonl(args.dataset, limit=args.limit)

    details: list[dict[str, Any]] = []
    for case in cases:
        pred = call_agent(args.agent_url, case)
        details.append(evaluate_case(case, pred))

    metrics = aggregate(details)
    report = {
        "config": {
            "dataset": str(args.dataset),
            "agent_url": args.agent_url,
            "limit": args.limit,
        },
        "metrics": metrics,
        "details": details,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    print(json.dumps({"metrics": metrics, "output": str(args.output)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
