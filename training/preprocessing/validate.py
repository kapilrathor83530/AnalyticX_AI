"""Validate instruction dataset: schemas, duplicates, length."""
import json
import sys
from pathlib import Path


def validate(path: Path) -> dict:
    total = 0
    errors = []
    seen = set()

    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {i}: invalid json ({exc})")
                continue

            for key in ("instruction", "output"):
                if not record.get(key):
                    errors.append(f"line {i}: missing {key}")

            key = (record.get("instruction"), record.get("input"), record.get("output"))
            if key in seen:
                errors.append(f"line {i}: duplicate")
            seen.add(key)

    return {"total": total, "errors": errors}


if __name__ == "__main__":
    result = validate(Path(sys.argv[1]))
    print(json.dumps(result, indent=2))
    if result["errors"]:
        sys.exit(1)
