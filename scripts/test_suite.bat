@echo off
echo =====================================================================
echo  Running AI SEO Test Suite
echo =====================================================================

cd /d "%~dp0\.."
call .\venv\Scripts\activate.bat
pytest -v tests/
pause
