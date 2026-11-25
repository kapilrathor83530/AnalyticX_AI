"""Evaluate base vs fine-tuned model on held-out test set."""
import argparse
import json
from pathlib import Path

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


def load_model(base_model: str, adapter: str | None):
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    return model, tokenizer


def generate(model, tokenizer, prompt: str, max_new_tokens: int = 256) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
        )
    return tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--test-set", required=True)
    parser.add_argument("--output", default="./outputs/eval_report.json")
    args = parser.parse_args()

    base_model, tokenizer = load_model(args.base_model, adapter=None)
    ft_model, _ = load_model(args.base_model, adapter=args.adapter)

    tests = [json.loads(line) for line in Path(args.test_set).read_text().splitlines() if line.strip()]

    results = []
    for test in tests:
        prompt = test["instruction"]
        base_out = generate(base_model, tokenizer, prompt)
        ft_out = generate(ft_model, tokenizer, prompt)
        expected = test.get("output", "")
        results.append(
            {
                "instruction": prompt,
                "expected": expected,
                "base_output": base_out,
                "ft_output": ft_out,
                "base_exact": base_out.strip() == expected.strip(),
                "ft_exact": ft_out.strip() == expected.strip(),
            }
        )

    base_score = sum(r["base_exact"] for r in results) / len(results)
    ft_score = sum(r["ft_exact"] for r in results) / len(results)

    report = {
        "total": len(results),
        "base_exact_match": base_score,
        "ft_exact_match": ft_score,
        "delta": ft_score - base_score,
        "results": results,
    }

    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"Base exact: {base_score:.4f}  FT exact: {ft_score:.4f}  Delta: {ft_score - base_score:.4f}")
    print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
