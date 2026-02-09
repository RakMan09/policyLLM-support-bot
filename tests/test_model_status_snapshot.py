from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_model_status_snapshot import render_markdown


def test_render_markdown_contains_core_fields():
    md = render_markdown(
        {
            "mode": "hybrid",
            "enabled": True,
            "ready": True,
            "model_id": "mistralai/Mistral-7B-Instruct-v0.2",
            "adapter_dir": "models/dpo_qlora/adapter",
            "missing_artifacts": [],
            "load_error": None,
        }
    )
    assert "# Model Runtime Status" in md
    assert "- mode: hybrid" in md
    assert "- ready: True" in md
    assert "models/dpo_qlora/adapter" in md
