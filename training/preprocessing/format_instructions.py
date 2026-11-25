"""Convert cleaned records into chat format for TRL SFTTrainer."""
import json
from pathlib import Path
from typing import Any, Dict


SYSTEM_PROMPT = (
    "You are Analyticx AI, a business analytics assistant. "
    "Answer with verified reasoning only. If data is insufficient, say exactly what is missing."
)


def to_chat(record: Dict[str, str]) -> Dict[str, Any]:
    user_content = record["instruction"]
    if record.get("input"):
        user_content = f"{user_content}\n\nInput:\n{record['input']}"

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": record["output"]},
        ]
    }


def format_file(input_path: Path, output_path: Path) -> int:
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            record = json.loads(line)
            dst.write(json.dumps(to_chat(record)) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    import sys

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    print(f"Formatted {format_file(src, dst)} records")
