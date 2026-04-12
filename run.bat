@echo off
title AgroSage — Start Server
color 0A

echo.
echo  ======================================================
echo   AgroSage — Agricultural Intelligence Platform
echo  ======================================================
echo.

:: ── Check Python ──────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: ── Navigate to script folder ─────────────────────────────
cd /d "%~dp0"

:: ── Create venv if missing ────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo  [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: ── Activate venv ─────────────────────────────────────────
call venv\Scripts\activate.bat

:: ── Install / upgrade dependencies ────────────────────────
echo  [SETUP] Installing dependencies (this may take a moment on first run)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [WARNING] Some packages may have failed to install.
)

:: ── Train crop model if not present ───────────────────────
if not exist "models\saved\crop_model.pkl" (
    echo.
    echo  [MODEL] Crop model not found — training with synthetic data...
    python models\train_crop.py --synthetic
    echo  [MODEL] Crop model trained.
)

:: ── Start Flask ───────────────────────────────────────────
echo.
echo  [SERVER] Starting Flask on http://localhost:5000
echo  [SERVER] Press Ctrl+C to stop.
echo.

python app.py

echo.
echo  [SERVER] Server stopped.
pause
