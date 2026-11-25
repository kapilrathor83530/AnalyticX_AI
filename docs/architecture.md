# Architecture

See project root README and the Part 1–5 reference. Summary:

- Frontend: React + TypeScript + Vite + Tailwind + Plotly + React Three Fiber + react-grid-layout
- Backend: FastAPI + SQLAlchemy + Pandas + NumPy + SciPy + scikit-learn + statsmodels
- Persistence: SQLite (dev), PostgreSQL-compatible models
- LLM: Ollama + Qwen2.5 3B Instruct (optional, replaceable)
- Agents: deterministic sequential orchestrator with validation layer
- Fine-tuning: QLoRA on Colab (separate training/ directory)
