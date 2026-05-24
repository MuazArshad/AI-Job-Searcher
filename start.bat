@echo off
title AI Job Hunting Agent
color 0A
echo.
echo  ============================================
echo    AI Job Hunting Agent - Starting Up...
echo  ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

:: Install dependencies if needed
echo [1/3] Installing Python dependencies...
pip install -r backend\requirements.txt -q

echo.
echo [2/3] Checking .env configuration...
findstr /C:"your_groq_api_key_here" .env >nul 2>&1
if not errorlevel 1 (
    echo.
    echo  ┌─────────────────────────────────────────┐
    echo  │  ACTION REQUIRED: Add your Groq key!    │
    echo  │                                         │
    echo  │  Open .env and replace:                 │
    echo  │  your_groq_api_key_here                 │
    echo  │  with your actual Groq API key          │
    echo  │                                         │
    echo  │  Get a free key at:                     │
    echo  │  https://console.groq.com/keys          │
    echo  └─────────────────────────────────────────┘
    echo.
    pause
)

echo.
echo [3/3] Starting server...
echo.
echo  Open your browser and go to:
echo  http://localhost:8000
echo.
echo  Press Ctrl+C to stop the server.
echo.

cd backend
python main.py

pause
