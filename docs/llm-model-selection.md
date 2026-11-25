# Analyticx AI / Analyticx AI model selection

Checked: 15 October 2026. This decision is for a 16 GB RAM Windows computer
with CPU-only local inference. The LLM plans and explains; Python analytics is
the source of truth for every number.

## Decision

**Local production model:** `qwen3:4b-instruct` using Ollama's Q4 build.
The Ollama registry lists it at about **2.5 GB** with tool support. In the
application the model context is capped at 8,192 tokens, one request is allowed
at a time, and tools receive compact schema/profile summaries rather than raw
tables. This leaves practical RAM for Windows, Python/Pandas, and the browser.

**Fine-tuning base:** `Qwen/Qwen3-4B` instruct weights with LoRA/QLoRA on a
cloud GPU. Qwen publishes Qwen3-4B under Apache-2.0, a materially simpler
commercial licensing position than Llama's community license or Gemma's gated
terms. Export the adapter, evaluate it, then merge/convert only after verifying
the specific conversion path. Do not assume a PEFT adapter can be loaded by
Ollama directly.

## Shortlist

| Candidate | Tool/structured-output suitability | CPU-local practicality | License / decision |
| --- | --- | --- | --- |
| Qwen3 4B Instruct | Official card describes agentic/tool use; Ollama supports schema-constrained output | Q4 download ~2.5 GB; selected | Apache-2.0; selected for production and fine-tuning |
| Qwen3 1.7B | Faster, but less reasoning headroom for ambiguous business questions | ~1.4 GB Q4 | Apache-2.0; fallback for slow CPUs |
| Llama 3.2 3B Instruct | Mature local tooling; generally capable | practical after quantization | Llama community license; not selected because Qwen's license is simpler |
| Gemma 3 4B / FunctionGemma | Gemma 3 has long context; FunctionGemma is purpose-built for task-specific calling | practical class of model | Gemma terms/access apply; FunctionGemma needs task fine-tuning and is not a dialogue replacement |
| Mistral Small 3.1 | Function calling documented, but substantially too large for a comfortable 16 GB shared-RAM deployment | not recommended locally | not selected; current documentation marks this release retired |

## Evidence and limits

- [Qwen3-4B official model card](https://huggingface.co/Qwen/Qwen3-4B) lists Apache-2.0, local-app quantization links, thinking controls and agentic-use guidance.
- [Ollama Qwen3 tags](https://ollama.com/library/qwen3/tags) lists the 4B instruct Q4 build at 2.5 GB and the 1.7B Q4 build at 1.4 GB.
- [Ollama structured output documentation](https://ollama.com/blog/structured-outputs) supports JSON Schema-constrained outputs, which this project validates again with Pydantic.
- [Llama 3.2 3B model page](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) identifies the Llama 3.2 license, rather than Apache-2.0.
- [Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3) documents the family context sizes; [FunctionGemma card](https://ai.google.dev/gemma/docs/functiongemma/model_card) states it is intended to be fine-tuned for specific function-calling workflows.
- [Mistral Small 3.1 documentation](https://docs.mistral.ai/models/mistral-small-3-1-25-03) documents function calling and notes this release is retired.

Download size is not total RAM use: KV cache, runtime overhead, the Python
server, datasets, and the browser all consume memory. The project therefore
does not expose the advertised 256K model context window.

## What has and has not been measured

The repository includes a reproducible benchmark and records latency/RAM when
you run it with a local model. No fine-tuned adapter or comparative score is
claimed until those commands have actually been run. Base-model quality should
be accepted only after the held-out benchmark passes at an acceptable rate.

## Windows installation

1. Install Ollama for Windows from [ollama.com](https://ollama.com/download).
2. In PowerShell run `ollama pull qwen3:4b-instruct`.
3. Start the application backend and frontend normally. Verify with
   `http://127.0.0.1:8000/api/v1/llm/health`.
4. For a slower/low-memory machine, set `DEFAULT_MODEL=qwen3:1.7b-q4_K_M` in
   `backend/.env`, restart the backend, and pull that exact model.

The API never sends prompts to a paid provider. If Ollama is stopped or the
model is absent, deterministic analytics remains available and the LLM API
reports unavailable status.

## Safety architecture

`POST /api/v1/llm/plan` is a planning endpoint, not a code executor. It uses a
JSON Schema, Pydantic model validation, an allow-list of analytical tools,
column-name validation, and a maximum plan length. No LLM-generated Python,
SQL, shell command, or JavaScript is executed.
