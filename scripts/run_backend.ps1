Push-Location backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
Pop-Location
