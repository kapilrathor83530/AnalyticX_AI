"""Cloud-only QLoRA starter for the selected Qwen3 4B base model.

Run after installing transformers, datasets, trl, peft, accelerate and a CUDA-
compatible bitsandbytes build. This script intentionally fails early on no-GPU.
"""
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="Qwen/Qwen3-4B")
    parser.add_argument("--epochs", type=float, default=2)
    args = parser.parse_args()

    import torch
    if not torch.cuda.is_available():
        raise SystemExit("A CUDA GPU runtime is required for this QLoRA recipe; no training was started.")
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    dataset = load_dataset("json", data_files=args.train, split="train")
    if not len(dataset) or "messages" not in dataset.column_names:
        raise SystemExit("Training JSONL must contain at least one `messages` example.")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        device_map="auto",
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4"),
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM"),
        args=SFTConfig(output_dir=args.output, num_train_epochs=args.epochs, per_device_train_batch_size=1,
                       gradient_accumulation_steps=8, learning_rate=2e-4, logging_steps=5, save_strategy="epoch"),
    )
    trainer.train()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)


if __name__ == "__main__":
    main()
