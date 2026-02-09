# Model Runtime Status

Snapshot of local LLM runtime readiness.

- mode: hybrid
- enabled: True
- ready: True
- model_id: mistralai/Mistral-7B-Instruct-v0.2
- adapter_dir: models/dpo_qlora/adapter
- missing_artifacts: None
- load_error: None

## Notes
- `ready=true` means expected adapter files are present.
- In `hybrid` mode, runtime may still fallback to deterministic behavior if loading fails.
