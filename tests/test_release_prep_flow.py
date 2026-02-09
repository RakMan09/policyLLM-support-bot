from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.release_prep as release_prep


def _noop_json(path: Path) -> dict:
    return {}


def test_release_prep_runs_ship_ready_gate_by_default(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str]) -> None:
        calls.append(cmd)

    monkeypatch.setattr(release_prep, "run", _fake_run)
    monkeypatch.setattr(release_prep, "load_json", _noop_json)

    template_path = tmp_path / "docs/RELEASE_NOTES_TEMPLATE.md"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text("decision_accuracy: <value>\npass_rate: <value>\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        release_prep,
        "parse_args",
        lambda: type(
            "Args",
            (),
            {
                "repo_root": Path("."),
                "output_notes": Path("docs/RELEASE_NOTES.md"),
                "skip_audit": True,
                "skip_gate": False,
                "gate_max_age_hours": 168.0,
                "run_demo": False,
                "run_runtime_smoke": False,
                "runtime_smoke_require_ready": False,
                "agent_url": "http://localhost:8002",
            },
        )(),
    )

    release_prep.main()
    flat = [" ".join(x) for x in calls]
    assert any("scripts/ship_ready_gate.py" in c for c in flat)


def test_release_prep_skips_gate_when_requested(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str]) -> None:
        calls.append(cmd)

    monkeypatch.setattr(release_prep, "run", _fake_run)
    monkeypatch.setattr(release_prep, "load_json", _noop_json)

    template_path = tmp_path / "docs/RELEASE_NOTES_TEMPLATE.md"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text("decision_accuracy: <value>\npass_rate: <value>\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        release_prep,
        "parse_args",
        lambda: type(
            "Args",
            (),
            {
                "repo_root": Path("."),
                "output_notes": Path("docs/RELEASE_NOTES.md"),
                "skip_audit": True,
                "skip_gate": True,
                "gate_max_age_hours": 168.0,
                "run_demo": False,
                "run_runtime_smoke": False,
                "runtime_smoke_require_ready": False,
                "agent_url": "http://localhost:8002",
            },
        )(),
    )

    release_prep.main()
    flat = [" ".join(x) for x in calls]
    assert not any("scripts/ship_ready_gate.py" in c for c in flat)


def test_release_prep_runs_runtime_smoke_and_requires_gate_when_enabled(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str]) -> None:
        calls.append(cmd)

    monkeypatch.setattr(release_prep, "run", _fake_run)
    monkeypatch.setattr(release_prep, "load_json", _noop_json)

    template_path = tmp_path / "docs/RELEASE_NOTES_TEMPLATE.md"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text("decision_accuracy: <value>\npass_rate: <value>\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        release_prep,
        "parse_args",
        lambda: type(
            "Args",
            (),
            {
                "repo_root": Path("."),
                "output_notes": Path("docs/RELEASE_NOTES.md"),
                "skip_audit": True,
                "skip_gate": False,
                "gate_max_age_hours": 168.0,
                "run_demo": False,
                "run_runtime_smoke": True,
                "runtime_smoke_require_ready": True,
                "agent_url": "http://localhost:8002",
            },
        )(),
    )

    release_prep.main()
    flat = [" ".join(x) for x in calls]
    assert any("scripts/runtime_readiness_smoke.py" in c for c in flat)
    gate_cmds = [c for c in flat if "scripts/ship_ready_gate.py" in c]
    assert gate_cmds
    assert "--require-runtime-smoke" in gate_cmds[0]
