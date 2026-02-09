from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from services.agent_server.app.llm_runtime import check_llm_runtime_ready


def render_markdown(status: dict[str, Any]) -> str:
    missing = status.get("missing_artifacts", [])
    missing_text = ", ".join(missing) if missing else "None"
    lines = [
        "# Model Runtime Status",
        "",
        "Snapshot of local LLM runtime readiness.",
        "",
        f"- mode: {status.get('mode', 'N/A')}",
        f"- enabled: {status.get('enabled', 'N/A')}",
        f"- ready: {status.get('ready', 'N/A')}",
        f"- model_id: {status.get('model_id', 'N/A')}",
        f"- adapter_dir: {status.get('adapter_dir', 'N/A')}",
        f"- missing_artifacts: {missing_text}",
        f"- load_error: {status.get('load_error', 'N/A')}",
        "",
        "## Notes",
        "- `ready=true` means expected adapter files are present.",
        "- In `hybrid` mode, runtime may still fallback to deterministic behavior if loading fails.",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate model runtime readiness snapshot artifacts.")
    parser.add_argument("--json-output", type=Path, default=Path("eval/results/model_runtime_status.json"))
    parser.add_argument("--md-output", type=Path, default=Path("docs/MODEL_STATUS.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    status = check_llm_runtime_ready().as_dict()

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(status, ensure_ascii=True, indent=2), encoding="utf-8")

    md = render_markdown(status)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.write_text(md, encoding="utf-8")

    print(
        json.dumps(
            {
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
                "ready": status.get("ready"),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
