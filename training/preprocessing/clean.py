"""Clean and normalize raw instruction data."""
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def normalize_record(record: Dict[str, Any]) -> Dict[str, str]:
    instruction = str(record.get("instruction", "")).strip()
    input_text = str(record.get("input", "") or "").strip()
    output = str(record.get("output", "")).strip()

    if not instruction or not output:
        raise ValueError("Instruction and output are required")

    return {"instruction": instruction, "input": input_text, "output": output}


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def clean_file(input_path: Path, output_path: Path) -> int:
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in iter_jsonl(input_path):
            try:
                normalized = normalize_record(record)
            except ValueError:
                continue
            f.write(json.dumps(normalized) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    import sys

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    n = clean_file(src, dst)
    print(f"Cleaned {n} records -> {dst}")
