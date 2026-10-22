import asyncio
import logging
from typing import Dict, Any, List
from urllib.parse import quote
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.workflows.gsc.sitemaps")

class GSCSitemapsManager:
    """
    Browser-first Sitemaps submission and status tracking in Google Search Console.
    """

    def __init__(self, browser: BrowserController):
        self.browser = browser

    async def navigate_to_sitemaps(self, property_id: str) -> Dict[str, Any]:
        encoded_prop = quote(property_id, safe='')
        url = f"https://search.google.com/search-console/sitemaps?resource_id={encoded_prop}"
        return await self.browser.navigate(url, wait_until="networkidle")

    async def get_submitted_sitemaps(self) -> List[Dict[str, Any]]:
        """Reads table of existing submitted sitemaps, status, and discovered pages."""
        page = await self.browser.get_page()
        try:
            sitemaps = await page.evaluate("""() => {
                const results = [];
                const rows = document.querySelectorAll("table tbody tr");
                for (const row of rows) {
                    const cols = Array.from(row.querySelectorAll("td")).map(c => c.innerText.trim());
                    if (cols.length >= 3) {
                        results.push({
                            sitemap_url: cols[0] || '',
                            type: cols[1] || '',
                            submitted_date: cols[2] || '',
                            last_read: cols[3] || '',
                            status: cols[4] || '',
                            discovered_pages: cols[5] || '0'
                        });
                    }
                }
                return results;
            }""")
            return sitemaps
        except Exception as e:
            logger.warning(f"Error reading sitemaps table: {e}")
            return []

    async def submit_sitemap(self, sitemap_path_or_url: str) -> Dict[str, Any]:
        """
        Enters sitemap relative path or full URL into the input field and clicks Submit.
        Verifies the submission dialog or feedback alert in the UI.
        """
        page = await self.browser.get_page()
        try:
            # Find the sitemap input field
            input_locator = page.locator("input[aria-label*='Add a new sitemap'], input[placeholder*='sitemap.xml']").first
            if await input_locator.count() == 0:
                # Try generic input in the top section
                input_locator = page.locator("form input[type='text']").first

            if await input_locator.count() == 0:
                return {
                    "success": False,
                    "error": "Could not locate sitemap input field in Search Console interface."
                }

            # Type sitemap path
            await BrowserActions.human_type(page, input_locator, sitemap_path_or_url)
            await BrowserActions.human_delay(400, 700)

            # Click Submit button (exact=True avoids matching 'Submit feedback')
            submit_btn = page.get_by_role("button", name="Submit", exact=True)
            if await submit_btn.count() == 0:
                submit_btn = page.locator("div[role='button']:has-text('Submit'), button:has-text('Submit')").filter(has_not_text="feedback")

            pre_shot = await BrowserActions.capture_screenshot(page, "before_sitemap_submit")

            if await submit_btn.count() > 0:
                try:
                    await submit_btn.first.click(timeout=5000)
                except Exception:
                    # Fallback to pressing Enter on the input if button is visually covered or transitioning
                    await page.keyboard.press("Enter")
            else:
                await page.keyboard.press("Enter")

            await BrowserActions.human_delay(2000, 4000)

            post_shot = await BrowserActions.capture_screenshot(page, "after_sitemap_submit")
            page_text = await page.evaluate("() => document.body ? document.body.innerText : ''")

            success = "Sitemap submitted" in page_text or "Success" in page_text
            
            # Dismiss 'Got it' dialog if Google shows the acknowledgment modal
            got_it_btn = page.get_by_role("button", name="Got it", exact=True)
            if await got_it_btn.count() > 0:
                await got_it_btn.first.click()
                await BrowserActions.human_delay(200, 500)

            return {
                "success": success,
                "sitemap": sitemap_path_or_url,
                "message": "Sitemap submitted successfully and acknowledged by Google." if success else "Sitemap submission could not be verified automatically.",
                "screenshots": {"before": pre_shot, "after": post_shot}
            }
        except Exception as e:
            logger.error(f"Error submitting sitemap: {e}")
            return {"success": False, "error": str(e)}
