@echo off
title Sales Forecasting System
echo =====================================================================
echo  Enterprise Sales Forecasting System Using Machine Learning
echo =====================================================================
echo.

REM Check if python is in PATH
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please ensure Python is installed and added to PATH.
    pause
    exit /b
)

echo [INFO] Starting Sales Forecasting Server...
echo [INFO] Dashboard will be accessible at: http://localhost:5000
echo.

REM Open browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

python app.py

pause
