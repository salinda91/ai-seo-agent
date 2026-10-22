import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseCMSAutomation
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.workflows.cms.woocommerce")

class WooCommerceAutomation(BaseCMSAutomation):
    """
    Automates product-level SEO, meta tags, and image alt text updates
    inside WooCommerce product catalog.
    """

    async def update_product_seo(
        self,
        db: AsyncSession,
        website_id: int,
        admin_base_url: str,
        product_title: str,
        public_url: str,
        new_meta_description: str,
        recommendation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        page = await self.browser.get_page()
        admin_base = admin_base_url.rstrip("/")
        if not admin_base.endswith("/wp-admin"):
            admin_base = f"{admin_base}/wp-admin"

        products_url = f"{admin_base}/edit.php?post_type=product"
        nav_res = await self.browser.navigate(products_url)
        if not nav_res["success"]:
            return {"success": False, "error": "Could not access WooCommerce products page."}

        try:
            # Search for the product
            search_input = page.locator("#post-search-input")
            if await search_input.count() > 0:
                await BrowserActions.human_type(page, search_input, product_title)
                await page.keyboard.press("Enter")
                await BrowserActions.human_delay(1500, 2500)

            # Find product title link
            prod_link = page.locator("a.row-title").first
            if await prod_link.count() == 0:
                return {"success": False, "error": f"Product '{product_title}' not found."}

            await prod_link.click()
            await page.wait_for_load_state("domcontentloaded")
            await BrowserActions.human_delay(1500, 2500)

            # Update Yoast/RankMath/WooCommerce product description
            desc_input = page.locator("#yoast_wpseo_metadesc, #rank_math_description, textarea[name='excerpt']").first
            before_val = ""
            if await desc_input.count() > 0:
                before_val = (await desc_input.input_value()) or ""
                await BrowserActions.human_type(page, desc_input, new_meta_description)

            # Save product
            save_btn = page.locator("input#publish, button.editor-post-publish-button, button:has-text('Update')").first
            pre_shot = await BrowserActions.capture_screenshot(page, "before_woo_save")
            await save_btn.click()
            await BrowserActions.human_delay(2000, 3500)
            post_shot = await BrowserActions.capture_screenshot(page, "after_woo_save")

            verified_live = await self.verify_live_change(public_url, "meta_description", new_meta_description)

            rec = await self.record_change(
                db=db,
                website_id=website_id,
                recommendation_id=recommendation_id,
                url=public_url,
                field_name="meta_description",
                before_val=before_val,
                after_val=new_meta_description,
                status="verified" if verified_live else "applied"
            )

            return {
                "success": True,
                "verified_live": verified_live,
                "change_record_id": rec.id,
                "screenshots": {"before": pre_shot, "after": post_shot}
            }
        except Exception as e:
            logger.error(f"WooCommerce update error: {e}")
            return {"success": False, "error": str(e)}
