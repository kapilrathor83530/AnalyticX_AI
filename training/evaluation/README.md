# Analyticx AI LLM benchmark

This held-out set tests tool selection, structured schema validity, clarification
handling, chart intent, and unsupported causal claims. It is deliberately not
included in the example fine-tuning data.

From `backend` after installing and running the selected Ollama model:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python ..\training\evaluation\evaluate_planner.py --output ..\training\evaluation\base_qwen3_4b.json
```

Run it before and after an adapter conversion using identical settings, retain
both JSON reports, and only claim improvement if the held-out results improve.
Record model tag, Ollama version, context setting, CPU, RAM, and any failures.
For recommendation usefulness, add blinded human review using a documented
rubric; do not infer that quality from tool-match rate alone.
