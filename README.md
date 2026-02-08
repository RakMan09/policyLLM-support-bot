# refund-returns-agent

Generic, policy-grounded Refund/Returns Agent portfolio project.

It includes:
- data pipeline from public datasets
- deterministic policy engine for labels/rewards
- tool-based support backend (FastAPI + Postgres)
- guarded agent orchestration
- SFT + DPO training pipelines
- evaluation + safety suite
- Streamlit UI
- Docker Compose local stack + GitHub Actions CI

## Architecture
```text
Customer/UI (Streamlit)
        |
        v
Agent Server (FastAPI)
  - guardrails (injection/fraud/exfiltration)
  - tool orchestration
  - customer reply + internal summary
        |
        v
Tool Server (FastAPI)
  - lookup_order
  - get_policy
  - check_eligibility
  - compute_refund
  - create_return
  - create_label
  - create_escalation
        |
        v
Postgres
  - orders, returns, labels, escalations
  - tool_call_logs

Offline ML
  raw datasets -> preprocess/build synthetic -> SFT prep/train -> DPO prep/train
                                  |
                                  v
                           eval harness + safety suite
```

## Repository Layout
```text
refund-returns-agent/
  services/
    tool_server/
    agent_server/
    ui/
  pipelines/
  training/
  eval/
  infra/db/
  data/
    raw/        # gitignored
    processed/  # generated artifacts
  tests/
  .github/workflows/
```

## Local Setup
Requirements:
- Python 3.11+
- Docker + Docker Compose
- (Optional) CUDA GPU host for full SFT/DPO training

Install:
```bash
cd "/Users/raksh/Desktop/Refund Returns Agent"
python3 -m pip install -e '.[dev]'
cp .env.example .env
```

Run stack:
```bash
docker compose up --build
```

Health checks:
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

UI:
- `http://localhost:8501`

## Public Data Ingestion
Place datasets under:
- `data/raw/olist/`
- `data/raw/twitter/`
- `data/raw/tweetsumm/`

Pipeline commands:
```bash
python3 pipelines/preprocess_text.py --raw-dir data/raw --processed-dir data/processed --max-rows 200000
python3 pipelines/build_dataset.py --raw-dir data/raw --processed-dir data/processed --max-cases 5000 --seed 42
```

## Training
Install training extras:
```bash
python3 -m pip install -e '.[train]'
```

SFT prepare-only:
```bash
python3 training/sft_train.py \
  --prepare-only \
  --train-cases data/processed/synthetic_cases_train.jsonl \
  --val-cases data/processed/synthetic_cases_val.jsonl \
  --tweetsumm data/processed/tweetsumm_pairs.jsonl \
  --prepared-train data/processed/sft_train_prepared.jsonl \
  --prepared-val data/processed/sft_val_prepared.jsonl
```

SFT QLoRA (CUDA host):
```bash
python3 training/sft_train.py \
  --model mistral-7b-instruct-v0.2 \
  --train-cases data/processed/synthetic_cases_train.jsonl \
  --val-cases data/processed/synthetic_cases_val.jsonl \
  --tweetsumm data/processed/tweetsumm_pairs.jsonl \
  --output-dir models/sft_qlora
```

DPO prepare-only:
```bash
python3 training/dpo_train.py \
  --prepare-only \
  --train-pairs data/processed/dpo_pairs_train.jsonl \
  --prepared-train data/processed/dpo_train_prepared.jsonl \
  --prepared-val data/processed/dpo_val_prepared.jsonl
```

DPO (CUDA host):
```bash
python3 training/dpo_train.py \
  --model mistral-7b-instruct-v0.2 \
  --train-pairs data/processed/dpo_pairs_train.jsonl \
  --output-dir models/dpo_qlora \
  --adapter-init-dir models/sft_qlora/adapter
```

Model export (requires successful SFT adapter):
```bash
python3 training/export_model.py \
  --base-model mistralai/Mistral-7B-Instruct-v0.2 \
  --adapter-dir models/sft_qlora/adapter \
  --output-dir models/sft_merged
```

## Evaluation
Offline eval harness:
```bash
python3 eval/eval_harness.py \
  --dataset data/processed/synthetic_cases_test.jsonl \
  --agent-url http://localhost:8002 \
  --limit 200 \
  --output eval/results/eval_report.json
```

Safety suite:
```bash
python3 eval/safety_suite.py \
  --agent-url http://localhost:8002 \
  --output eval/results/safety_report.json
```

Human eval rubric:
- `eval/human_eval.md`

## Testing and Linting
```bash
ruff check .
pytest -q
```

## Demo Assets
Add screenshots/GIF placeholders under `docs/` and link them here:
- `docs/screenshots/ui-main.png`
- `docs/screenshots/tool-trace.png`
- `docs/screenshots/eval-report.png`

## GitHub Hosting Steps
1. Initialize and push:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/refund-returns-agent.git
git push -u origin main
```

2. Add CI:
- Workflow is included at `.github/workflows/ci.yml`.

3. Secrets:
- Do not commit `.env`.
- Add any required secrets in GitHub repository settings -> Secrets and variables -> Actions.

4. Git LFS (optional for large artifacts):
```bash
git lfs install
git lfs track "*.safetensors" "*.bin" "*.pt"
git add .gitattributes
git commit -m "Track large model artifacts with Git LFS"
```

5. Releases/tags:
```bash
git tag -a v0.1.0 -m "Initial portfolio release"
git push origin v0.1.0
```
- Upload trained adapters as release assets instead of committing multi-GB artifacts.

## Safety + Guardrails
- Policy engine is the final authority on approvals.
- Customer text is treated as untrusted input.
- Prompt injection/fraud/exfil attempts trigger refusal or safe fallback.
- Logs and outputs mask sensitive fields.
- Tool use is allowlisted and schema-constrained.

## License
MIT. See `LICENSE`.
