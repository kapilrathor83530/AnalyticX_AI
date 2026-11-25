Write-Host "Setting up Analyticx AI..."

# Backend
Push-Location backend
if (-not (Test-Path .venv)) {
    py -3.11 -m venv .venv
}
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Pop-Location

# Frontend
Push-Location frontend
npm install
Pop-Location

Write-Host "Setup complete."
Write-Host "Start backend:  .\scripts\run_backend.ps1"
Write-Host "Start frontend: .\scripts\run_frontend.ps1"
Write-Host "Optional LLM:   ollama serve  (after ollama pull qwen2.5:3b-instruct-q4_K_M)"
