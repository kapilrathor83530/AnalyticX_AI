"""Reproducible held-out planner evaluation.

This evaluates plan validity and expected-tool precision/recall; it does not
claim numerical-answer quality, which must be evaluated against deterministic
tool results in a separate test set.
"""
import argparse
import asyncio
import json
import platform
import time
from pathlib import Path

try:
    import psutil
except ImportError:  # Optional on minimal environments.
    psutil = None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(Path(__file__).with_name("analyticx_benchmark.jsonl")))
    parser.add_argument("--output", default="evaluation_report.json")
    args = parser.parse_args()
    # Backend package import needs: run from backend, or set PYTHONPATH=backend.
    from app.llm.tool_planner import create_plan

    cases = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    process = psutil.Process() if psutil else None
    before = process.memory_info().rss if process else None
    for case in cases:
        started = time.perf_counter()
        plan = await create_plan(case["question"], case["columns"])
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        actual = {step.tool for step in plan.plan}
        expected = set(case["expected_tools"])
        rows.append({
            "id": case["id"], "latency_ms": elapsed_ms,
            "expected_tools": sorted(expected), "actual_tools": sorted(actual),
            "tool_match": actual == expected,
            "clarification_match": plan.clarification_needed == case["requires_clarification"],
        })
    matches = sum(row["tool_match"] for row in rows)
    clarifications = sum(row["clarification_match"] for row in rows)
    report = {
        "benchmark": "analyticx held-out planner set",
        "cases": len(rows), "tool_exact_match_rate": matches / len(rows) if rows else 0,
        "clarification_accuracy": clarifications / len(rows) if rows else 0,
        "latency_ms": {"mean": round(sum(row["latency_ms"] for row in rows) / len(rows), 2) if rows else 0},
        "process_rss_delta_bytes": process.memory_info().rss - before if process and before is not None else None,
        "platform": platform.platform(), "results": rows,
        "note": "Scores are measured only when this command is executed against an installed local model.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
