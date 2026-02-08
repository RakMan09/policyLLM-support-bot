from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into base model for export")
    parser.add_argument("--base-model", required=True, help="HF base model id used for SFT")
    parser.add_argument("--adapter-dir", type=Path, required=True, help="Path to saved LoRA adapter")
    parser.add_argument("--output-dir", type=Path, default=Path("models/sft_merged"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    adapter_config = args.adapter_dir / "adapter_config.json"
    adapter_weights = args.adapter_dir / "adapter_model.safetensors"
    adapter_weights_bin = args.adapter_dir / "adapter_model.bin"

    if not adapter_config.exists() or (not adapter_weights.exists() and not adapter_weights_bin.exists()):
        raise FileNotFoundError(
            "Adapter files not found. Expected at least:\n"
            f"- {adapter_config}\n"
            f"- {adapter_weights} (or {adapter_weights_bin})\n"
            "Run SFT training on a CUDA host first to generate adapter artifacts."
        )

    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base = AutoModelForCausalLM.from_pretrained(args.base_model)
    model = PeftModel.from_pretrained(base, str(args.adapter_dir))
    merged = model.merge_and_unload()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(args.output_dir))

    tok = AutoTokenizer.from_pretrained(str(args.adapter_dir))
    tok.save_pretrained(str(args.output_dir))

    print(
        json.dumps(
            {
                "base_model": args.base_model,
                "adapter_dir": str(args.adapter_dir),
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
