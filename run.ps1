Write-Host "Starting Analyticx AI Platform..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm --prefix frontend run dev"
Write-Host "Analyticx AI is running!" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Yellow
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Yellow
