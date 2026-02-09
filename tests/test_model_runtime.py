from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.agent_server.app.config import settings
from services.agent_server.app.llm_runtime import check_llm_runtime_ready
from services.agent_server.app.main import app


def test_llm_runtime_ready_when_adapter_artifacts_exist(tmp_path: Path):
    adapter = tmp_path / "adapter"
    adapter.mkdir(parents=True, exist_ok=True)
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_text("x", encoding="utf-8")

    previous = settings.llm_adapter_dir
    try:
        settings.llm_adapter_dir = str(adapter)
        status = check_llm_runtime_ready()
        assert status.ready is True
        assert status.missing == []
    finally:
        settings.llm_adapter_dir = previous


def test_chat_model_status_endpoint():
    with TestClient(app) as client:
        response = client.get("/chat/model/status")
    assert response.status_code == 200
    body = response.json()
    assert "mode" in body
    assert "model_id" in body
    assert "adapter_dir" in body
    assert "ready" in body
    assert "missing_artifacts" in body
