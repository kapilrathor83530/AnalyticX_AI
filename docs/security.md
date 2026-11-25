# Security

- JWT auth (stub). Multi-user separation is designed but not fully enforced in MVP.
- Uploads validated by extension + size. Content sniffing is not yet enforced server-side.
- No arbitrary code execution from LLM output.
- Prompt injection is mitigated by never executing instructions found in data.
- Local mode sends no data to external LLMs.
- Do not commit `.env` or model weights.
10. Final Run & Test
powershell
# 1. Setup
.\scripts\setup_windows.ps1

# 2. Start backend
.\scripts\run_backend.ps1

# 3. Start frontend (new terminal)
.\scripts\run_frontend.ps1

# 4. Optional local LLM
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama serve

# 5. Tests
.\scripts\run_tests.ps1
