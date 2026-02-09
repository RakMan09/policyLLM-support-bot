from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.build_human_eval_packet import read_jsonl, sample_transcripts, write_scoring_template


def test_sample_transcripts_respects_size():
    rows = [
        {"case_id": f"C{i}", "final_status_chip": "Resolved" if i % 2 == 0 else "Denied"}
        for i in range(10)
    ]
    out = sample_transcripts(rows, sample_size=6, seed=7)
    assert len(out) == 6
    ids = {r["case_id"] for r in out}
    assert len(ids) == 6


def test_read_jsonl_and_sheet(tmp_path: Path):
    inp = tmp_path / "in.jsonl"
    inp.write_text(
        "\n".join(
            [
                json.dumps({"case_id": "C1", "final_status_chip": "Resolved"}),
                json.dumps({"case_id": "C2", "final_status_chip": "Denied"}),
            ]
        ),
        encoding="utf-8",
    )
    rows = read_jsonl(inp)
    assert len(rows) == 2

    sheet = tmp_path / "sheet.csv"
    write_scoring_template(rows, sheet)
    content = sheet.read_text(encoding="utf-8")
    assert "case_id,final_status_chip,clarity" in content
    assert "C1,Resolved" in content
