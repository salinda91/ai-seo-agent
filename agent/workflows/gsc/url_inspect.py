import asyncio
import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import quote
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.workflows.gsc.url_inspect")

class GSCURLInspector:
    """
    Browser-first URL Inspection & Indexing Request workflow.
    Inspects live status and triggers Googlebot indexing requests when eligible.
    """

    def __init__(self, browser: BrowserController):
        self.browser = browser

    async def inspect_url(self, property_id: str, target_url: str) -> Dict[str, Any]:
        """
        Loads the Search Console property and uses the universal top search bar
        ('Inspect any URL in [property]') to trigger live URL inspection without 404s.
        """
        encoded_prop = quote(property_id, safe='')
        base_gsc_url = f"https://search.google.com/search-console?resource_id={encoded_prop}"
        
        logger.info(f"Navigating to GSC property home for URL inspection: {base_gsc_url}")
        await self.browser.navigate(base_gsc_url, wait_until="domcontentloaded", timeout_ms=45000)
        page = await self.browser.get_page()
        await BrowserActions.human_delay(1500, 2500)

        # Look for the top inspection search input
        input_locator = page.locator("input[placeholder*='Inspect any URL'], input[aria-label*='Inspect any URL']").first
        if await input_locator.count() == 0:
            input_locator = page.locator("header input[type='text'], [role='search'] input, input[type='search']").first

        if await input_locator.count() == 0:
            # Fallback: navigate to performance page which always renders the inspection search bar in header
            perf_url = f"https://search.google.com/search-console/performance/search-analytics?resource_id={encoded_prop}"
            await self.browser.navigate(perf_url, wait_until="domcontentloaded", timeout_ms=30000)
            await BrowserActions.human_delay(1500, 2500)
            input_locator = page.locator("input[placeholder*='Inspect any URL'], input[aria-label*='Inspect any URL']").first

        if await input_locator.count() > 0:
            logger.info(f"Submitting target URL '{target_url}' into GSC inspection search bar...")
            await input_locator.click()
            await BrowserActions.human_delay(200, 400)
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            for char in target_url:
                await page.keyboard.type(char)
                await asyncio.sleep(0.015)
            await BrowserActions.human_delay(250, 500)
            await page.keyboard.press("Enter")
            logger.info("Pressed Enter. Waiting for Google Search Console index retrieval...")
        else:
            logger.warning("Could not find top inspection search bar in Search Console interface.")

        # Wait for Google's live inspection retrieval modal or result
        for _ in range(15):
            await asyncio.sleep(2)
            current_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
            if "URL is on Google" in current_text or "URL is not on Google" in current_text or "Request indexing" in current_text or "REQUEST INDEXING" in current_text:
                break

        shot = await BrowserActions.capture_screenshot(page, "gsc_url_inspected")
        page_text = await page.evaluate("() => document.body ? document.body.innerText : ''")

        # Parse presence status
        is_on_google = "URL is on Google" in page_text
        is_indexed = is_on_google and "Page is indexed" in page_text
        
        # Check for indexing request eligibility
        can_request_indexing = "Request indexing" in page_text or "REQUEST INDEXING" in page_text

        # Extract details
        details = []
        if "Crawled - currently not indexed" in page_text:
            details.append("Crawled - currently not indexed")
        if "Discovered - currently not indexed" in page_text:
            details.append("Discovered - currently not indexed")
        if "Duplicate without user-selected canonical" in page_text:
            details.append("Duplicate without user-selected canonical")
        if "Page with redirect" in page_text:
            details.append("Page with redirect")

        return {
            "success": True,
            "target_url": target_url,
            "is_on_google": is_on_google,
            "is_indexed": is_indexed,
            "can_request_indexing": can_request_indexing,
            "status_details": details,
            "screenshot": shot
        }

    async def request_indexing(self) -> Dict[str, Any]:
        """
        Clicks 'Request indexing' button in the current inspection view.
        Monitors the live testing modal and verifies submission.
        """
        page = await self.browser.get_page()
        try:
            req_btn = page.locator("button:has-text('Request indexing'), div[role='button']:has-text('Request indexing'), button:has-text('REQUEST INDEXING'), div[role='button']:has-text('REQUEST INDEXING')")
            if await req_btn.count() == 0:
                req_btn = page.get_by_role("button", name=re.compile(r"Request indexing", re.I))

            if await req_btn.count() == 0:
                return {
                    "success": False,
                    "message": "'Request indexing' button not found or quota already reached."
                }

            pre_shot = await BrowserActions.capture_screenshot(page, "before_request_indexing")
            await req_btn.first.click()
            logger.info("Clicked 'Request indexing'. Waiting for Google live test (up to 45s)...")

            # Google tests the live URL before opening dialog (usually takes 10-30s)
            start_wait = asyncio.get_event_loop().time()
            accepted = False
            
            for _ in range(30):
                await asyncio.sleep(2)
                text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                if "Indexing requested" in text:
                    accepted = True
                    break
                if "Quota exceeded" in text:
                    return {
                        "success": False,
                        "quota_exceeded": True,
                        "message": "Daily Google indexing request quota has been exceeded."
                    }

            post_shot = await BrowserActions.capture_screenshot(page, "after_request_indexing")

            # Click 'Got it' dialog if presented
            got_it = page.locator("button:has-text('Got it'), div[role='button']:has-text('Got it')")
            if await got_it.count() > 0:
                await got_it.first.click()
                await BrowserActions.human_delay(200, 500)

            return {
                "success": accepted,
                "accepted": accepted,
                "message": "Indexing request submitted and accepted by Google." if accepted else "Indexing request could not be confirmed.",
                "screenshots": {"before": pre_shot, "after": post_shot}
            }
        except Exception as e:
            logger.error(f"Error requesting indexing: {e}")
            return {"success": False, "error": str(e)}
