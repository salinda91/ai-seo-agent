@echo off
setlocal
echo =====================================================================
echo  Starting Autonomous Browser-Controlled AI SEO Specialist Agent
echo =====================================================================

cd /d "%~dp0\.."

:: Check if port 8765 is currently in use and terminate the previous instance
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r ":8765\>.*LISTENING"') do (
    echo [INFO] Port 8765 is occupied by PID %%a. Terminating previous instance...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 /nobreak >nul
)

call .\venv\Scripts\activate.bat
python -m agent.run_agent --port 8765
pause
