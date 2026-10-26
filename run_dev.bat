@echo off
echo ===================================================
echo Starting GovPolicy AI Local Development Environment
echo ===================================================

:: Ensure we are in project root
cd /d "%~dp0"

:: 1. Activate or create Python virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating Python virtual environment (.venv)...
    python -m venv .venv
    echo Installing backend dependencies...
    .\.venv\Scripts\pip.exe install -r backend\requirements.txt
) else (
    echo [1/3] Virtual environment (.venv) detected.
)

:: 2. Seed raw data sources if missing
echo [2/3] Seeding Singapore datasets...
.\.venv\Scripts\python.exe backend\data\seed_data.py

:: 3. Launch Backend & Frontend servers
echo [3/3] Launching local servers...
echo Starting Backend (FastAPI) on http://localhost:8000 ...
start "GovPolicy Backend (FastAPI)" cmd /k ".\.venv\Scripts\activate.bat && set DEBUG=true && set ENVIRONMENT=development && python backend\run.py"

echo Starting Frontend (Vite HMR) on http://localhost:3000 ...
start "GovPolicy Frontend (Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo Local Development Servers are running!
echo - Frontend (Hot Reload): http://localhost:3000
echo - Backend API:           http://localhost:8000
echo - Swagger Docs:          http://localhost:8000/docs
echo ===================================================
