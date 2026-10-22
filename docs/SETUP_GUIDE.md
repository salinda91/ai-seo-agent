# Setup & Quickstart Guide

## 1. Overview
The **Autonomous Browser-Controlled AI SEO Agent** operates on a **Browser UI First** principle. It automates Google Search Console and website CMS operations through real browser interactions in an isolated, dedicated Chrome profile.

No Google Search Console API credentials, OAuth client secrets, or Google passwords are required.

---

## 2. Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Google Chrome:** Installed at `C:\Program Files\Google\Chrome\Application\chrome.exe`
- **Python:** 3.12+ (Python 3.14 recommended)
- **Node.js:** v18+ with npm

---

## 3. Installation

### Option A: Using the Automated Windows Script
Simply run:
```cmd
scripts\install.bat
```
This script creates the Python virtual environment, installs backend dependencies, and builds the Chrome extension into `extension/dist`.

### Option B: Manual Installation
1. Set up Python virtual environment:
   ```cmd
   python -m venv venv
   .\venv\Scripts\pip install -r agent\requirements.txt
   ```
2. Build the Chrome extension:
   ```cmd
   cd extension
   npm install
   npm run build
   cd ..
   ```

---

## 4. One-Time Setup: Logging into Google & CMS
The agent uses a **dedicated Chrome profile directory**:
`%LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile`

This ensures your personal browsing history, cookies, and passwords remain completely untouched and separate.

1. Double-click `scripts\launch_dedicated_chrome.bat` (or open Chrome with `--user-data-dir="%LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile"`).
2. In the opened browser window:
   - Navigate to [Google Search Console](https://search.google.com/search-console) and log into your Google account normally. Complete any 2FA/MFA requirements.
   - Navigate to your website admin panel (e.g. `https://yoursite.com/wp-admin`) and log in.
3. Close the browser window or leave it open. Your cookies and sessions are now permanently stored in the dedicated profile.

---

## 5. Starting the Automation Agent
Launch the local agent server:
```cmd
scripts\start_agent.bat
```
Or manually:
```cmd
.\venv\Scripts\python -m agent.run_agent --port 8765
```

The agent will display:
- **Server URL:** `http://127.0.0.1:8765`
- **Dedicated Profile:** `%LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile`
- **Pairing Secret Token:** `(32-character random hex token)`

Copy the **Pairing Secret Token**.

---

## 6. Installing the Chrome Extension
1. Open Google Chrome.
2. In the address bar, go to: `chrome://extensions`
3. Toggle on **Developer mode** in the top-right corner.
4. Click **Load unpacked** in the top-left.
5. Select the directory:
   `c:\Users\HomePC\Documents\my Projects\ai_seo\extension\dist`
6. Click the extension puzzle piece icon in Chrome, find **AI SEO Agent**, and click **Open AI SEO Side Panel**.
7. In the Side Panel, navigate to **Settings**, paste your **Pairing Secret Token**, and click **Save & Pair Extension**.

---

## 7. Connecting Your First Website
1. Open the **Websites** tab in the Side Panel.
2. Click **+ Add Website**.
3. Enter your domain (e.g. `example.com`), CMS platform (WordPress, WooCommerce, Laravel, or Custom), and Admin URL.
4. Choose an **Automation Mode**:
   - **Recommendation Mode:** Suggestions only.
   - **Supervised Mode (Recommended):** Proposes changes; executes only upon your explicit approval.
   - **Autonomous Mode:** Auto-executes verified low-risk meta tag optimizations within the 50 actions/day limit.
5. Click **Connect Website**.
