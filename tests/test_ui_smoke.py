from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_ui_file_exists_and_has_entrypoint():
    p = REPO_ROOT / "services" / "ui" / "app.py"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "st.title(" in content
    assert "Run Agent" in content
    assert "Tool Trace" in content
