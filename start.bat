@echo off
echo Starting Analyticx AI Platform...
echo ===================================
start "Analyticx Backend" cmd /k "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload"
timeout /t 2 >nul
start "Analyticx Frontend" cmd /k "npm --prefix frontend run dev"
echo Both services launched!
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000
