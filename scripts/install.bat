@echo off
echo =====================================================================
echo  AI SEO Specialist Agent - Windows Setup & Installation
echo =====================================================================

cd /d "%~dp0\.."

echo [1/3] Creating Python Virtual Environment...
if not exist "venv" (
    python -m venv venv
)

echo [2/3] Installing Python Dependencies...
call .\venv\Scripts\activate.bat
pip install -r agent\requirements.txt

echo [3/3] Installing Chrome Extension Dependencies & Building...
cd extension
call npm install
call npm run build
cd ..

echo.
echo =====================================================================
echo  Installation Complete!
echo  Next steps:
echo  1. Run scripts\launch_dedicated_chrome.bat to log into Google once.
echo  2. Run scripts\start_agent.bat to start the automation server.
echo  3. Load the extension in Chrome: chrome://extensions -> Load unpacked -> extension\dist
echo =====================================================================
pause
