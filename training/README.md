# Business instruction data and fine-tuning

`business_instruction_examples.jsonl` is a **format example**, not a sufficient
training corpus. Add licensed business datasets and convert verified tool
interactions into chat examples. Keep source records, licenses, transformations,
and a dataset hash in a manifest. Never train on confidential uploads without
documented authorization.

## Data quality rules

- Targets must be generated from verified tool results, never guessed numbers.
- Keep evaluation prompts and source rows separate from training data.
- Include clarification, malformed-output, unsupported-claim, and privacy cases.
- Validate every line as JSON and enforce the planning schema before training.

## Cloud QLoRA recipe

Use a cloud GPU; CPU-only Windows is not a practical QLoRA training target.
Install compatible versions in an isolated environment and run:

```bash
python train_qlora.py --train business_instruction_examples.jsonl --output ./artifacts/qwen3-bi-lora
```

`bitsandbytes` availability depends on the chosen CUDA runtime. Record the
actual GPU, CUDA version, package versions, steps, loss, and evaluation results;
the script deliberately does not fabricate those values.
