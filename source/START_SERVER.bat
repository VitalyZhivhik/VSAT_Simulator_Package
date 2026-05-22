@echo off
title VSAT Simulator Server
echo ============================================
echo   VSAT Simulator - Starting Server
echo ============================================
echo.

:: Use bundled portable Python (no installation needed)
set PYTHON=%~dp0python\python.exe

if not exist "%PYTHON%" (
    echo Bundled Python not found, trying system Python...
    set PYTHON=python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERROR: Python not found. Re-download the full package.
        echo.
        pause
        exit /b 1
    )
)

echo Using: %PYTHON%
echo.
echo Starting server... (close this window to stop)
echo.
"%PYTHON%" run.py

echo.
echo ============================================
echo   Server stopped.
echo ============================================
echo.
echo If this was unexpected, check logs\vsat_server.log
echo.
pause
