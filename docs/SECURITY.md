# Security & Profile Isolation Architecture

## 1. Browser Profile Isolation
- **Dedicated User-Data-Directory:** All browser automation runs using a dedicated user data folder located at `%LOCALAPPDATA%\AI_SEO_Agent\ChromeProfile`.
- **Zero Attachment to Personal Browsing:** The agent never attaches to, inspects, or reads tabs, cookies, or history from your personal Chrome profile.
- **Stealth & Bot Protection:** Launches Chrome using clean, human-like flags (`--disable-blink-features=AutomationControlled`, natural user-agent).

---

## 2. Localhost Protection & Pairing Secret Token
- **Localhost Binding:** The automation server strictly binds to `127.0.0.1:8765`. It refuses external connections.
- **Origin Validation:** The FastAPI CORS middleware restricts origins exclusively to:
  - `chrome-extension://*`
  - `http://127.0.0.1:*` / `http://localhost:*`
- **Pairing Secret Token:** Every request and WebSocket connection must provide the secret token in the `X-Agent-Token` header or query string.
- Tokens are automatically generated using 24 cryptographically secure random bytes (`secrets.token_hex(24)`) and stored locally in `agent/data/.agent_token`.

---

## 3. Crawler SSRF & Private Network Protection
To prevent Server-Side Request Forgery (SSRF), internal network scanning, or cloud metadata leakage during crawling:
1. Every URL is parsed before retrieval.
2. The hostname is resolved to all associated IP addresses.
3. If any resolved IP belongs to any private or reserved subnet, request is immediately blocked:
   - `0.0.0.0/8`
   - `10.0.0.0/8`
   - `127.0.0.0/8` (Loopback)
   - `169.254.0.0/16` (Link-Local & Cloud Metadata endpoint `169.254.169.254`)
   - `172.16.0.0/12`
   - `192.168.0.0/16`
   - `100.64.0.0/10`
   - `::1/128`, `fc00::/7`, `fe80::/10`
4. Requests to `metadata.google.internal`, `localhost`, or AWS `instance-data` are explicitly blocked by hostname.

---

## 4. Prompt Injection Defense
- All HTML content, page titles, descriptions, and headings retrieved from external websites are treated as **untrusted data**.
- Text is sanitized via `sanitize_untrusted_text()`, stripping control characters, null bytes, and limiting length.
- Foreign website text is fed only as data parameters into Gemini prompts and never injected as system instructions.

---

## 5. Hardcoded High-Impact Governance Gates
The agent engine strictly enforces that the following operations **NEVER** execute autonomously, regardless of the automation mode:
- Deleting or unpublishing pages or posts.
- Altering URL permalink structures or slugs.
- Modifying site-wide canonical tags or robots.txt.
- Modifying redirect tables (301/302).
- Changing credentials, user accounts, or permissions.

All such actions require explicit human approval via the Task Queue.
