# Google Search Console — Browser-Only Guide

## 1. Operating Principle
**Browser UI First. No Search Console API Dependency.**

Google Search Console API has rate limits, restricted features, requires GCP projects and service account keys, and frequently lacks the newest UI controls. The AI SEO Agent automates the official Search Console web interface directly at `https://search.google.com/search-console` using your authenticated browser session.

---

## 2. Supported Browser Workflows

### A. Adding a Website Property
1. The agent opens Search Console and inspects the property selector combobox.
2. If the domain is already listed, it selects it.
3. If not, it opens the **Add Property** modal.
4. It inputs either the Domain property (`example.com`) or URL prefix (`https://example.com/`).
5. It inspects the verification modal:
   - If auto-verified via existing account rights (e.g. Google Analytics or Google Tag Manager), it logs success.
   - If an HTML tag or HTML file is required, it captures the tag and offers to install it in your CMS.
   - If a DNS TXT record is required, it displays the exact TXT record for you to add in your registrar (e.g. Cloudflare, Namecheap, GoDaddy).
6. **Integrity Rule:** The agent never claims a property is verified unless Google's interface displays "Ownership verified".

### B. Analyzing Search Performance
1. Selects the target property.
2. Navigates to `/search-console/performance/search-analytics`.
3. Activates the 4 primary scorecards: Total Clicks, Total Impressions, Average CTR, Average Position.
4. Clicks the **QUERIES** tab, extracts table rows, handles pagination, and saves queries to the local SQLite database.
5. Clicks the **PAGES** tab to discover which landing pages are gaining or losing visibility.
6. The AI Keyword Researcher processes these queries to calculate **Opportunity Scores (0-100)**:
   - Queries ranking on Page 2 (positions 11-20) with high impressions are flagged as "Striking Distance" opportunities.
   - High-impression queries with CTR < 2% trigger meta description and title tag optimization recommendations.

### C. Submitting Sitemaps
1. Navigates to `/search-console/sitemaps`.
2. Checks existing sitemaps table (Status: Success, Couldn't fetch, Has errors).
3. Discovers sitemap URLs via `robots.txt` or website inspection.
4. Types the sitemap path (e.g., `sitemap.xml`) into the "Add a new sitemap" input and clicks **Submit**.
5. Waits for Google's confirmation dialog, confirms "Sitemap submitted", and clicks "Got it".

### D. Inspecting URLs & Requesting Indexing
1. Navigates to `/search-console/inspect`.
2. Enters target page URL and presses Enter.
3. Waits for live Googlebot index coverage evaluation (up to 45 seconds).
4. Extracts presence on Google, index coverage errors, canonical status, and mobile friendliness.
5. If the URL is eligible and unindexed, it clicks **Request Indexing**.
6. Awaits live testing completion.
7. Detects daily indexing quotas if exceeded and stops politely without hammering the UI.

---

## 3. Workflows Requiring Manual Human Intervention
1. **Google Account Sign-In / 2FA:** Initial login or periodic Google password re-authentication.
2. **DNS TXT Record Updates:** Domain-level DNS additions must be made in your DNS provider.
3. **CAPTCHA / Security Challenges:** If Google displays a reCAPTCHA challenge, the agent automatically pauses and notifies you in the Side Panel to solve it.
