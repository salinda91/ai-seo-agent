import asyncio
import logging
from typing import Dict, Any, List, Optional
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.workflows.gsc.property")

GSC_BASE_URL = "https://search.google.com/search-console"

class GSCPropertyManager:
    """
    Browser-first Google Search Console Property Manager.
    Interacts directly with search.google.com/search-console UI.
    """

    def __init__(self, browser: BrowserController):
        self.browser = browser

    async def open_search_console(self) -> Dict[str, Any]:
        """Navigates to GSC and checks for authentication status."""
        try:
            result = await self.browser.navigate(GSC_BASE_URL, wait_until="domcontentloaded")
            if not result.get("success"):
                return result
            
            page = await self.browser.get_page()
            # Check if user needs to log into Google
            url = page.url
            title = await page.title()
            if "accounts.google.com" in url or "Sign in" in title:
                return {
                    "success": False,
                    "needs_login": True,
                    "message": "User is not logged into Google in the dedicated browser session. Please log in.",
                    "screenshot": result.get("screenshot", "")
                }
            return {"success": True, "needs_login": False, "url": url, "screenshot": result.get("screenshot", "")}
        except Exception as e:
            logger.error(f"Error opening search console: {e}")
            return {
                "success": False,
                "needs_login": False,
                "message": f"Browser navigation error: {str(e)}",
                "error": str(e)
            }

    async def list_properties(self) -> List[str]:
        """
        Extracts existing verified/unverified properties from the Search Console property dropdown.
        """
        page = await self.browser.get_page()
        properties = []
        try:
            # Click the property selector button in GSC top left / navigation
            # Look for property selector by aria-label or role
            selector = "div[aria-label*='Search property'], div[role='combobox'], [data-test-id='property-selector']"
            elem = await page.query_selector(selector)
            if elem:
                await elem.click()
                await BrowserActions.human_delay(300, 600)
                
                # Read property items from dropdown
                items = await page.query_selector_all("[role='option'], [data-resource-id]")
                for it in items:
                    text = (await it.inner_text()).strip()
                    if text and text not in properties and not text.startswith("Add property"):
                        properties.append(text)
                # Press Escape to close dropdown
                await page.keyboard.press("Escape")
        except Exception as e:
            logger.warning(f"Error reading property list: {e}")
        return properties

    async def add_property(self, domain_or_url: str, is_domain_property: bool = False) -> Dict[str, Any]:
        """
        Initiates the Add Property wizard in Search Console.
        Reads the verification requirements and reports back without fabricating success.
        """
        page = await self.browser.get_page()
        try:
            # Open property selector
            selector = "div[aria-label*='Search property'], div[role='combobox']"
            elem = await page.query_selector(selector)
            if elem:
                await elem.click()
                await BrowserActions.human_delay(400, 800)

            # Look for "+ Add property" button
            add_button = page.get_by_text("Add property", exact=False)
            if await add_button.count() > 0:
                await add_button.first.click()
                await BrowserActions.human_delay(500, 1000)

            shot_wizard = await BrowserActions.capture_screenshot(page, "gsc_add_property_modal")

            # Determine whether Domain or URL Prefix input
            if is_domain_property:
                # Left side: Domain property (requires DNS TXT record)
                input_locator = page.locator("input[placeholder*='example.com'], input[aria-label*='Domain']").first
            else:
                # Right side: URL prefix property
                input_locator = page.locator("input[placeholder*='https://'], input[aria-label*='URL prefix']").first

            if await input_locator.count() > 0:
                await BrowserActions.human_type(page, input_locator, domain_or_url)
                await BrowserActions.human_delay(300, 600)
                
                # Click Continue button
                continue_btn = page.get_by_role("button", name="Continue", exact=True)
                if await continue_btn.count() == 0:
                    continue_btn = page.locator("button:has-text('Continue'), div[role='button']:has-text('Continue')")
                if await continue_btn.count() > 0:
                    await continue_btn.first.click()
                    await BrowserActions.human_delay(2000, 3500)

            shot_result = await BrowserActions.capture_screenshot(page, "gsc_verification_instructions")
            page_text = await page.evaluate("() => document.body ? document.body.innerText : ''")

            # Inspect if already verified or requires specific method
            is_verified = "Ownership verified" in page_text or "Auto-verified" in page_text
            
            # Extract instructions
            instructions = "Verification modal opened."
            if "Ownership verified" in page_text:
                instructions = "Ownership successfully auto-verified via existing account credentials!"
            elif "DNS record" in page_text:
                instructions = "DNS TXT record verification required. Please add the DNS record provided in your domain registrar."
            elif "HTML file" in page_text or "HTML tag" in page_text:
                instructions = "HTML Tag / HTML File verification available. The agent can place the tag in the website CMS."

            return {
                "success": True,
                "domain_or_url": domain_or_url,
                "is_verified": is_verified,
                "instructions": instructions,
                "screenshot": shot_result
            }
        except Exception as e:
            logger.error(f"Failed to add property {domain_or_url}: {e}")
            shot_err = await BrowserActions.capture_screenshot(page, "gsc_add_prop_err")
            return {
                "success": False,
                "error": str(e),
                "screenshot": shot_err
            }
