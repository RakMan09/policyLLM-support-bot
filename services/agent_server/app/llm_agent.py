from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from services.agent_server.app.config import settings

logger = logging.getLogger("agent_server")


class LLMAdvisor:
    """Optional LLM helper for extraction and response drafting.

    In `deterministic` mode this class is a no-op.
    In `hybrid` or `llm` mode, failures gracefully fall back in `hybrid`.
    """

    def __init__(self) -> None:
        self.mode = settings.agent_mode.lower().strip()
        self.model_id = settings.llm_model_id
        self.adapter_dir = Path(settings.llm_adapter_dir)
        self.device = settings.llm_device
        self.dtype = settings.llm_dtype
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._load_error: str | None = None

    @property
    def enabled(self) -> bool:
        return self.mode in {"hybrid", "llm"}

    @property
    def hard_fail(self) -> bool:
        return self.mode == "llm"

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "model_id": self.model_id,
            "adapter_dir": str(self.adapter_dir),
            "loaded": self._model is not None and self._tokenizer is not None,
            "load_error": self._load_error,
        }

    def extract_reason(self, text: str, allowed_reasons: list[str]) -> str | None:
        if not self.enabled:
            return None
        prompt = (
            "Return strict JSON only.\n"
            "Task: infer support reason from user text.\n"
            f"Allowed reasons: {allowed_reasons}\n"
            "Schema: {\"reason\": <one allowed reason or null>}\n"
            f"User text: {text}"
        )
        payload = self._generate_json(prompt, max_new_tokens=80)
        if not payload:
            return None
        reason = payload.get("reason")
        if isinstance(reason, str) and reason in allowed_reasons:
            return reason
        return None

    def draft_reply(self, objective: str, context: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        prompt = (
            "Return strict JSON only.\n"
            "You are a customer-support assistant.\n"
            "Write one concise, policy-safe customer reply.\n"
            "Do not invent facts. Keep under 80 words.\n"
            f"Objective: {objective}\n"
            f"Context JSON: {json.dumps(context, ensure_ascii=True)}\n"
            "Schema: {\"reply\": \"...\"}"
        )
        payload = self._generate_json(prompt, max_new_tokens=120)
        if not payload:
            return None
        reply = payload.get("reply")
        if isinstance(reply, str) and reply.strip():
            return reply.strip()
        return None

    def _generate_json(self, prompt: str, max_new_tokens: int) -> dict[str, Any] | None:
        if not self._ensure_loaded():
            return None
        try:
            inputs = self._tokenizer(prompt, return_tensors="pt")
            device = getattr(self._model, "device", None)
            if device is not None:
                inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=None,
            )
            text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return None
            return json.loads(match.group(0))
        except Exception as exc:  # pragma: no cover - runtime dependent
            self._load_error = f"generation_failed: {exc}"
            logger.warning("llm_generation_failed error=%s", exc)
            if self.hard_fail:
                raise RuntimeError(f"LLM generation failed: {exc}") from exc
            return None

    def _ensure_loaded(self) -> bool:
        if not self.enabled:
            return False
        if self._model is not None and self._tokenizer is not None:
            return True
        if self._load_error and not self.hard_fail:
            return False

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            dtype_map = {
                "auto": "auto",
                "float16": torch.float16,
                "bfloat16": torch.bfloat16,
                "float32": torch.float32,
            }
            torch_dtype = dtype_map.get(self.dtype, "auto")
            model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
                device_map=self.device,
            )

            adapter_config = self.adapter_dir / "adapter_config.json"
            if adapter_config.exists():
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, str(self.adapter_dir))
            model.eval()

            self._model = model
            self._tokenizer = tokenizer
            self._load_error = None
            return True
        except Exception as exc:  # pragma: no cover - runtime dependent
            self._load_error = str(exc)
            logger.warning("llm_load_failed mode=%s error=%s", self.mode, exc)
            if self.hard_fail:
                raise RuntimeError(f"LLM load failed: {exc}") from exc
            return False
