from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def sample_transcripts(
    rows: list[dict[str, Any]],
    sample_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    if sample_size <= 0:
        return []
    if sample_size >= len(rows):
        return rows

    rnd = random.Random(seed)
    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        status = str(row.get("final_status_chip", "unknown"))
        by_status[status].append(row)

    statuses = sorted(by_status.keys())
    picked: list[dict[str, Any]] = []
    idx = 0

    # Round-robin by status to avoid single-class packets.
    while len(picked) < sample_size and statuses:
        status = statuses[idx % len(statuses)]
        bucket = by_status[status]
        if bucket:
            picked.append(bucket.pop(rnd.randrange(len(bucket))))
        else:
            statuses.remove(status)
            if not statuses:
                break
            continue
        idx += 1

    # If a bucket emptied early and we still need more, fill from remaining rows.
    if len(picked) < sample_size:
        remaining = [r for bucket in by_status.values() for r in bucket]
        rnd.shuffle(remaining)
        need = sample_size - len(picked)
        picked.extend(remaining[:need])

    return picked


def write_packet_jsonl(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def write_scoring_template(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "case_id",
        "final_status_chip",
        "clarity",
        "helpfulness",
        "correctness",
        "trustworthiness",
        "policy_adherence",
        "empathy",
        "safety_handling",
        "notes",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "case_id": row.get("case_id", ""),
                    "final_status_chip": row.get("final_status_chip", ""),
                    "clarity": "",
                    "helpfulness": "",
                    "correctness": "",
                    "trustworthiness": "",
                    "policy_adherence": "",
                    "empathy": "",
                    "safety_handling": "",
                    "notes": "",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 20-30 case human-eval packet from transcripts.")
    parser.add_argument(
        "--transcripts",
        type=Path,
        default=Path("eval/results/conversation_transcripts.jsonl"),
        help="Input transcripts JSONL from eval/conversation_eval.py",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=24,
        help="Target number of transcripts to sample (recommended 20-30)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--packet-output",
        type=Path,
        default=Path("eval/results/human_eval_packet.jsonl"),
    )
    parser.add_argument(
        "--sheet-output",
        type=Path,
        default=Path("eval/results/human_eval_sheet.csv"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("eval/results/human_eval_packet_summary.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.transcripts)
    sampled = sample_transcripts(rows, args.sample_size, args.seed)

    write_packet_jsonl(sampled, args.packet_output)
    write_scoring_template(sampled, args.sheet_output)

    by_status: dict[str, int] = defaultdict(int)
    for row in sampled:
        by_status[str(row.get("final_status_chip", "unknown"))] += 1

    summary = {
        "input_rows": len(rows),
        "sampled_rows": len(sampled),
        "sample_size_requested": args.sample_size,
        "status_distribution": dict(sorted(by_status.items())),
        "packet_output": str(args.packet_output),
        "sheet_output": str(args.sheet_output),
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "summary_output": str(args.summary_output)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
