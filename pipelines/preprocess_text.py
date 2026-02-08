from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ISSUE_PATTERNS: dict[str, re.Pattern[str]] = {
    "damaged": re.compile(r"\b(damaged|broken|cracked)\b", flags=re.IGNORECASE),
    "defective": re.compile(r"\b(defect|defective|not working|won't turn on)\b", flags=re.IGNORECASE),
    "wrong_item": re.compile(r"\b(wrong item|different item|not what i ordered)\b", flags=re.IGNORECASE),
    "not_as_described": re.compile(r"\b(not as described|misleading|different than)\b", flags=re.IGNORECASE),
    "changed_mind": re.compile(r"\b(change my mind|don't want|no longer want)\b", flags=re.IGNORECASE),
    "late_delivery": re.compile(r"\b(late|delayed|still not arrived|where is my order)\b", flags=re.IGNORECASE),
}


def clean_text(text: str) -> str:
    text = re.sub(r"http[s]?://\S+", "", text)
    text = re.sub(r"@\w+", "@brand", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_issue_type(text: str) -> str:
    for issue, pattern in ISSUE_PATTERNS.items():
        if pattern.search(text):
            return issue
    return "changed_mind"


def preprocess_twitter(twcs_path: Path, output_path: Path, max_rows: int | None = None) -> int:
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with twcs_path.open("r", encoding="utf-8", newline="") as src, output_path.open(
        "w", encoding="utf-8"
    ) as out:
        reader = csv.DictReader(src)
        for row in reader:
            inbound = str(row.get("inbound", "")).lower()
            if inbound not in {"true", "t", "1"}:
                continue
            text = clean_text(row.get("text", ""))
            if not text:
                continue
            record = {
                "source": "twitter_support",
                "tweet_id": row.get("tweet_id"),
                "author_id": row.get("author_id"),
                "text": text,
                "issue_type_hint": infer_issue_type(text),
            }
            out.write(json.dumps(record, ensure_ascii=True) + "\n")
            count += 1
            if max_rows is not None and count >= max_rows:
                break
    return count


def find_twcs_file(raw_dir: Path) -> Path | None:
    candidates = [
        raw_dir / "twitter" / "twcs.csv",
        raw_dir / "twitter" / "twcs" / "twcs.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted((raw_dir / "twitter").glob("**/twcs.csv"))
    return matches[0] if matches else None


def preprocess_tweetsumm(tweetsumm_dir: Path, output_path: Path, max_rows: int | None = None) -> int:
    if not tweetsumm_dir.exists():
        return 0
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(tweetsumm_dir.glob("*.jsonl")) + sorted(tweetsumm_dir.glob("*.csv"))
    with output_path.open("w", encoding="utf-8") as out:
        for file in files:
            if file.suffix == ".jsonl":
                with file.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        row = json.loads(line)
                        dialog = clean_text(str(row.get("dialogue", row.get("dialog", ""))))
                        summary = clean_text(str(row.get("summary", "")))

                        # Tweetsumm official files contain annotations with abstractive summaries.
                        if not summary and isinstance(row.get("annotations"), list):
                            annotations = row["annotations"]
                            first_ann = annotations[0] if annotations else {}
                            abstractive = first_ann.get("abstractive", []) if isinstance(first_ann, dict) else []
                            if abstractive:
                                summary = clean_text(" ".join(str(x) for x in abstractive))
                            if not dialog:
                                conv_id = row.get("conversation_id", "unknown")
                                dialog = f"conversation {conv_id}"

                        if not summary:
                            continue
                        record = {"source": "tweetsumm", "dialog": dialog, "summary": summary}
                        out.write(json.dumps(record, ensure_ascii=True) + "\n")
                        count += 1
                        if max_rows is not None and count >= max_rows:
                            return count
            elif file.suffix == ".csv":
                with file.open("r", encoding="utf-8", newline="") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        dialog = clean_text(str(row.get("dialogue", row.get("dialog", ""))))
                        summary = clean_text(str(row.get("summary", "")))
                        if not dialog or not summary:
                            continue
                        record = {"source": "tweetsumm", "dialog": dialog, "summary": summary}
                        out.write(json.dumps(record, ensure_ascii=True) + "\n")
                        count += 1
                        if max_rows is not None and count >= max_rows:
                            return count
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess Twitter support + TweetSumm text data.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Root raw data directory with twitter/ and tweetsumm/ subfolders.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Output directory for normalized JSONL files.",
    )
    parser.add_argument("--max-rows", type=int, default=None, help="Optional max rows per source.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    twitter_input = find_twcs_file(args.raw_dir)
    twitter_output = args.processed_dir / "twitter_support_texts.jsonl"
    tweetsumm_input = args.raw_dir / "tweetsumm"
    tweetsumm_output = args.processed_dir / "tweetsumm_pairs.jsonl"

    twitter_count = 0
    if twitter_input is not None:
        twitter_count = preprocess_twitter(twitter_input, twitter_output, max_rows=args.max_rows)

    tweetsumm_count = preprocess_tweetsumm(
        tweetsumm_input, tweetsumm_output, max_rows=args.max_rows
    )

    print(
        json.dumps(
            {
                "twitter_support_rows": twitter_count,
                "tweetsumm_rows": tweetsumm_count,
                "twitter_output": str(twitter_output),
                "tweetsumm_output": str(tweetsumm_output),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
