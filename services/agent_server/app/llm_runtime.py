from __future__ import annotations

from pathlib import Path

from services.agent_server.app.config import settings
from services.agent_server.app.llm_agent import LLMAdvisor


class LLMRuntimeStatus:
    def __init__(
        self,
        *,
        mode: str,
        model_id: str,
        adapter_dir: str,
        ready: bool,
        missing: list[str],
        enabled: bool,
        load_error: str | None,
    ):
        self.mode = mode
        self.model_id = model_id
        self.adapter_dir = adapter_dir
        self.ready = ready
        self.missing = missing
        self.enabled = enabled
        self.load_error = load_error

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "model_id": self.model_id,
            "adapter_dir": self.adapter_dir,
            "ready": self.ready,
            "missing_artifacts": self.missing,
            "enabled": self.enabled,
            "load_error": self.load_error,
        }


def expected_adapter_files(adapter_dir: Path) -> list[Path]:
    return [
        adapter_dir / "adapter_config.json",
        adapter_dir / "adapter_model.safetensors",
    ]


def check_llm_runtime_ready() -> LLMRuntimeStatus:
    adapter_dir = Path(settings.llm_adapter_dir)
    expected = expected_adapter_files(adapter_dir)
    missing = [str(p) for p in expected if not p.exists()]
    # adapter weights can be .safetensors or .bin
    if str(adapter_dir / "adapter_model.safetensors") in missing:
        bin_path = adapter_dir / "adapter_model.bin"
        if bin_path.exists():
            missing.remove(str(adapter_dir / "adapter_model.safetensors"))

    advisor = LLMAdvisor()

    return LLMRuntimeStatus(
        mode=settings.agent_mode,
        model_id=settings.llm_model_id,
        adapter_dir=str(adapter_dir),
        ready=len(missing) == 0,
        missing=missing,
        enabled=advisor.enabled,
        load_error=advisor.status().get("load_error"),
    )
