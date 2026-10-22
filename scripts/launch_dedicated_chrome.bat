@echo off
echo =====================================================================
echo  Launching Dedicated Chrome Session for AI SEO Automation
echo =====================================================================
echo Profile Directory: %LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile
echo.
echo Log into Google Search Console (https://search.google.com/search-console)
echo and your website admin panels (e.g. wp-admin) in this browser window.
echo The session cookies will be stored persistently in this isolated profile.
echo =====================================================================

if not exist "%LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile" (
    mkdir "%LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile"
)

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile" --remote-debugging-port=9222 --no-first-run --no-default-browser-check "https://search.google.com/search-console"
