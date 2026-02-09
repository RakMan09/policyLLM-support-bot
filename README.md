# ResolveFlow Support Chatbot

`refund-returns-agent` is a production-style portfolio project for a stateful, multi-turn customer-support chatbot that handles refund, return, replacement, cancellation, and escalation workflows end-to-end.

## What this project does
- Runs a real guided chat, not a single-shot form.
- Maintains session state and slot-filling in Postgres.
- Uses tool/function calling with strict schemas and logging.
- Applies policy as final authority for decisions and payout amounts.
- Supports evidence upload and validation for damage-related claims.
- Includes LLM training pipelines (SFT QLoRA + DPO), eval harnesses, guardrails, and release automation.

## Main use cases
- Refund request
- Return request
- Replacement request
- Cancel order (processing only)
- Wrong/missing item
- Damaged item (with evidence requirement)
- Late delivery
- No order ID fallback via email or phone-last4

## Tech stack
- `Python 3.11+`
- `FastAPI` for tool server and agent server
- `Postgres` for sessions, cases, orders, evidence metadata, and logs
- `Streamlit` for multi-turn chat UI
- `Pydantic` for strict request/response schemas
- `Transformers + PEFT + TRL` for QLoRA SFT and DPO
- `Docker Compose` for local orchestration
- `pytest + ruff` for test/lint quality gates
- `GitHub Actions` for CI smoke and release-prep checks

## Architecture
```text
Streamlit UI (chat + guided controls + timeline + test order panel)
    |
    v
Agent Server (FastAPI)
- conversation state machine + slot filling
- guardrails (injection/fraud/PII/refusal)
- LLM-assisted advisor modes (deterministic/hybrid/llm)
    |
    v
Tool Server (FastAPI)
- read/write tools with schema validation
- idempotent side-effect tools (return, label, replacement, escalation)
- evidence upload + validation + retrieval
    |
    v
Postgres + local evidence storage
- sessions, messages, tool traces, orders, status, evidence records
```

## LLM modes
Configured via `.env`:
- `AGENT_MODE=deterministic`: no model inference, pure policy/state machine
- `AGENT_MODE=hybrid`: LLM-assisted reasoning with deterministic fallback
- `AGENT_MODE=llm`: strict model path, fails when model is unavailable

Runtime status endpoint:
- `GET /chat/model/status`

## Run locally
```bash
cd "/Users/raksh/Desktop/Refund Returns Agent"
cp .env.example .env
docker compose up -d --build
```

Open:
- UI: `http://localhost:8501`
- Agent health: `http://localhost:8002/health`
- Tool health: `http://localhost:8001/health`

## How to use
1. Start a new chat.
2. Enter identifier (`order_id`, email, or phone last4).
3. Select order and item(s) from guided controls.
4. Choose issue/reason and preferred resolution.
5. Upload evidence when prompted.
6. Confirm satisfaction or continue to alternatives/escalation.
7. Resume any session later with session ID.

## Built-in test/demo features
- Create test orders directly from the UI.
- View live case timeline and status chips.
- Run scripted end-to-end scenarios:
```bash
python3 scripts/demo_scenarios.py --agent-url http://localhost:8002 --output eval/results/demo_scenarios.json
```

## Data, training, and eval
Datasets used:
- Olist e-commerce (orders/products/payments/shipping)
- Customer Support on Twitter (language patterns)
- TweetSumm (dialog summary supervision)
- Approach B evidence simulation support (catalog + anomaly dirs via `.env`)

Core scripts:
- `pipelines/build_dataset.py`
- `pipelines/build_conversation_dataset.py`
- `training/sft_train.py`
- `training/dpo_train.py`
- `eval/eval_harness.py`
- `eval/conversation_eval.py`
- `eval/safety_suite.py`
- `eval/stack_smoke.py`

## Quality + release commands
```bash
ruff check .
pytest -q
python3 scripts/release_prep.py --repo-root . --output-notes docs/RELEASE_NOTES.md --run-demo --run-runtime-smoke --runtime-smoke-require-ready --agent-url http://localhost:8002
python3 scripts/ship_ready_gate.py --repo-root . --max-age-hours 168 --require-runtime-smoke --output eval/results/ship_ready_gate.json
```

## Can this be hosted online?
Yes. This project can be deployed as a live demo website.

Recommended options:
1. `Render` or `Railway`: deploy 3 services (agent, tool, UI) + managed Postgres.
2. `Fly.io`: deploy FastAPI services and Streamlit as separate apps.
3. `AWS/GCP/Azure`: container services + managed database.

Deployment notes:
- Keep `AGENT_MODE=deterministic` for lightweight public demo without GPU.
- Use `AGENT_MODE=hybrid` with adapter artifacts mounted for richer behavior.
- Store secrets as platform env vars (never in git).
- Persist `/data/evidence` with attached volume/object storage.

## Documentation index
- `/Users/raksh/Desktop/Refund Returns Agent/docs/GITHUB_SETUP.md`
- `/Users/raksh/Desktop/Refund Returns Agent/docs/COLAB_RUNBOOK.md`
- `/Users/raksh/Desktop/Refund Returns Agent/docs/RELEASE_CHECKLIST.md`
- `/Users/raksh/Desktop/Refund Returns Agent/docs/MODEL_STATUS.md`
- `/Users/raksh/Desktop/Refund Returns Agent/docs/METRICS.md`
- `/Users/raksh/Desktop/Refund Returns Agent/docs/PORTFOLIO_REPORT.md`

One-command release prep (with live demos):
```bash
python3 scripts/release_prep.py --repo-root . --output-notes docs/RELEASE_NOTES.md --run-demo --agent-url http://localhost:8002
```

Demo scenarios:
```bash
python3 scripts/demo_scenarios.py --agent-url http://localhost:8002 --output eval/results/demo_scenarios.json
```

Portfolio report:
```bash
python3 scripts/generate_portfolio_report.py --output docs/PORTFOLIO_REPORT.md
```

Release manifest:
```bash
python3 scripts/generate_manifest.py --repo-root . --output dist/release_manifest.json
```

Ship-ready gate:
```bash
python3 scripts/ship_ready_gate.py --repo-root . --max-age-hours 168 --output eval/results/ship_ready_gate.json
```
