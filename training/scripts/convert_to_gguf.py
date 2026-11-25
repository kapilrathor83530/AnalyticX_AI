"""Convert LoRA adapter to GGUF for Ollama. Requires llama.cpp installed."""
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True, help="Path to PEFT adapter")
    parser.add_argument("--llama-cpp", default="../../llama.cpp", help="Path to llama.cpp repo")
    parser.add_argument("--out", default="../outputs/gguf/analyticx-qwen.gguf")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    convert_script = Path(args.llama_cpp) / "convert_lora_to_gguf.py"
    if not convert_script.exists():
        raise SystemExit(
            f"convert_lora_to_gguf.py not found in {args.llama_cpp}. "
            "Clone https://github.com/ggerganov/llama.cpp first."
        )

    cmd = [
        "python",
        str(convert_script),
        args.adapter,
        "--outfile",
        str(out_path),
        "--outtype",
        "f16",
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"GGUF saved to {out_path}")


if __name__ == "__main__":
    main()
