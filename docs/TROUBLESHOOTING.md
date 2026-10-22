# Troubleshooting & Recovery Guide

## 1. Challenge & Obstacle Detection (Human Takeover)

### How It Works:
The agent contains an active `ObstacleDetector` (`agent/browser/recovery.py`) that monitors the browser DOM and URL before and after every action.

When it detects:
- Cloudflare Turnstile / Challenge screens
- Google reCAPTCHA / hCaptcha / ArkoseLabs
- Google 2-Step Verification / MFA codes
- Google or WordPress session expiration ("Please sign in again")

### What to Do:
1. The agent immediately pauses its task queue and sets `manual_takeover: true`.
2. A prominent **Human Takeover** warning badge appears in the Chrome Extension Side Panel with an alert tone.
3. Simply switch to the dedicated Chrome browser window, solve the CAPTCHA or complete 2-Step Verification.
4. Once completed, click **Resume** in the Side Panel. The agent will reinspect the page and continue its workflow.

---

## 2. Common Issues & Solutions

### A. Extension Says "Agent Offline" or Red Dot
- **Cause:** The Python FastAPI server is not running or the port is blocked.
- **Fix:** 
  1. Open a terminal and run `scripts\start_agent.bat`.
  2. Verify that `http://127.0.0.1:8765/api/status` returns `{"status": "online"}` in your browser.

### B. Extension Says "Invalid or Missing X-Agent-Token"
- **Cause:** The pairing token entered in the extension Settings tab does not match `agent/data/.agent_token`.
- **Fix:**
  1. Open `agent/data/.agent_token` with Notepad.
  2. Copy the token.
  3. In the Chrome Extension, go to **Settings**, paste into **Agent Pairing Token**, and click **Save & Pair Extension**.

### C. Google Search Console Shows "Sign in" Screen
- **Cause:** You have not yet logged into Google inside the dedicated Chrome profile.
- **Fix:**
  1. Run `scripts\launch_dedicated_chrome.bat`.
  2. Sign into Google Search Console with your Google account.
  3. Once logged in, sessions persist automatically across automation runs.

### D. WordPress / WooCommerce Update Fails
- **Cause:** WordPress session expired, admin URL is incorrect, or post slug was not found.
- **Fix:**
  1. Verify the Admin URL in **Connected Websites** is formatted as `https://example.com/wp-admin`.
  2. Open the dedicated Chrome browser and verify you can view `https://example.com/wp-admin/edit.php`.
  3. Re-run the change approval.

---

## 3. Rollback Instructions
Every SEO modification made to your CMS is stored in the database with its exact `before_value` and `after_value`.
To revert any change:
1. In the Chrome Extension Side Panel, open **Opportunities** tab.
2. Click the **History** sub-tab.
3. Find the change you wish to undo and click the **Rollback** button.
4. The agent will navigate to the CMS post editor, restore the previous value, click Save, and verify the live website HTML.
