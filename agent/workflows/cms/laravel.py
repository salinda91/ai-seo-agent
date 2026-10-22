import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseCMSAutomation
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.workflows.cms.laravel")

class LaravelAdminAutomation(BaseCMSAutomation):
    """
    Automates SEO changes in Laravel-based administration panels
    such as Laravel Filament, Nova, or custom Blade/Inertia CRUD panels.
    """

    async def update_page_seo(
        self,
        db: AsyncSession,
        website_id: int,
        resource_edit_url: str,
        public_url: str,
        field_selectors: Dict[str, str],
        field_values: Dict[str, str],
        submit_selector: str = "button[type='submit']",
        recommendation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        page = await self.browser.get_page()
        nav_res = await self.browser.navigate(resource_edit_url)
        if not nav_res["success"]:
            return {"success": False, "error": f"Could not open Laravel resource URL {resource_edit_url}"}

        changes = []
        try:
            for field_name, selector in field_selectors.items():
                if field_name not in field_values:
                    continue
                new_val = field_values[field_name]
                input_el = page.locator(selector).first
                if await input_el.count() > 0:
                    before_val = (await input_el.input_value()) or ""
                    await BrowserActions.human_type(page, input_el, new_val)
                    changes.append((field_name, before_val, new_val))

            # Submit form
            submit_btn = page.locator(submit_selector).first
            if await submit_btn.count() == 0:
                submit_btn = page.get_by_role("button", name="Save").first

            pre_shot = await BrowserActions.capture_screenshot(page, "before_laravel_save")
            await submit_btn.click()
            await BrowserActions.human_delay(2000, 3500)
            post_shot = await BrowserActions.capture_screenshot(page, "after_laravel_save")

            # Verify on live site
            verified_live = True
            for field, _, new_val in changes:
                if field in ("meta_description", "title"):
                    ok = await self.verify_live_change(public_url, field, new_val)
                    if not ok:
                        verified_live = False

            saved_records = []
            for field, b_val, a_val in changes:
                rec = await self.record_change(
                    db=db,
                    website_id=website_id,
                    recommendation_id=recommendation_id,
                    url=public_url,
                    field_name=field,
                    before_val=b_val,
                    after_val=a_val,
                    status="verified" if verified_live else "applied"
                )
                saved_records.append(rec.id)

            return {
                "success": True,
                "changes": changes,
                "verified_live": verified_live,
                "change_records": saved_records,
                "screenshots": {"before": pre_shot, "after": post_shot}
            }
        except Exception as e:
            logger.error(f"Laravel admin update error: {e}")
            return {"success": False, "error": str(e)}
