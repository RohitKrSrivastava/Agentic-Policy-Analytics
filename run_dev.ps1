Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " Starting GovPolicy AI Local Development Environment" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# Set working directory to script location
Set-Location -Path $PSScriptRoot

# 1. Setup Python venv if missing
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[1/3] Creating Python virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
    & .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
} else {
    Write-Host "[1/3] Virtual environment (.venv) detected." -ForegroundColor Green
}

# 2. Seed datasets
Write-Host "[2/3] Seeding Singapore datasets..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe backend\data\seed_data.py

# 3. Launch Backend & Frontend servers
Write-Host "[3/3] Launching local servers..." -ForegroundColor Green
Write-Host "Starting Backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:DEBUG='true'; `$env:ENVIRONMENT='development'; .\.venv\Scripts\python.exe backend/run.py"

Write-Host "Starting Frontend on http://localhost:3000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location frontend; npm run dev"

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "Local Development Servers are running!" -ForegroundColor Cyan
Write-Host "- Frontend (Hot Reload): http://localhost:3000" -ForegroundColor White
Write-Host "- Backend API:           http://localhost:8000" -ForegroundColor White
Write-Host "- Swagger Docs:          http://localhost:8000/docs" -ForegroundColor White
Write-Host "===================================================`n" -ForegroundColor Cyan
