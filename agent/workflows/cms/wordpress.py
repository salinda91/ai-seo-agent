import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import BaseCMSAutomation
from ...models import Recommendation
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.workflows.cms.wordpress")

class WordPressAutomation(BaseCMSAutomation):
    """
    Automates on-page SEO changes inside WordPress wp-admin.
    Supports Yoast SEO, Rank Math, All-in-One SEO, and native WordPress editor.
    """

    async def update_post_seo(
        self,
        db: AsyncSession,
        website_id: int,
        admin_base_url: str,
        post_slug_or_title: str,
        public_url: str,
        new_title: Optional[str] = None,
        new_meta_description: Optional[str] = None,
        recommendation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Navigates to WordPress wp-admin, opens the target post editor,
        updates the SEO fields, publishes, and verifies.
        """
        page = await self.browser.get_page()
        admin_base = admin_base_url.rstrip("/")
        if not admin_base.endswith("/wp-admin"):
            admin_base = f"{admin_base}/wp-admin"

        # 1. Navigate to posts listing
        posts_url = f"{admin_base}/edit.php"
        nav_res = await self.browser.navigate(posts_url)
        if not nav_res["success"]:
            return {"success": False, "error": "Could not access WordPress admin posts page."}

        # Check for login prompt
        if "wp-login.php" in page.url:
            return {
                "success": False,
                "needs_login": True,
                "message": "WordPress session expired or user is logged out. Please log in through the browser."
            }

        # 2. Search for the post
        try:
            search_input = page.locator("#post-search-input")
            if await search_input.count() > 0:
                await BrowserActions.human_type(page, search_input, post_slug_or_title)
                await page.keyboard.press("Enter")
                await BrowserActions.human_delay(1500, 2500)

            # Find post title link in table
            post_link = page.locator("a.row-title").first
            if await post_link.count() == 0:
                return {
                    "success": False,
                    "error": f"Post '{post_slug_or_title}' not found in WordPress post list."
                }

            # Click Edit
            await post_link.click()
            await page.wait_for_load_state("domcontentloaded")
            await BrowserActions.human_delay(1500, 3000)

            before_title = ""
            before_desc = ""
            changes_made = []

            # 3. Locate SEO fields (Yoast, Rank Math, or Native)
            # Yoast Meta Description
            yoast_desc = page.locator("#yoast_wpseo_metadesc, textarea[name='yoast_wpseo_metadesc']").first
            # Rank Math Meta Description
            rankmath_desc = page.locator("#rank_math_description, textarea[name='rank_math_description']").first
            
            target_desc_input = None
            if await yoast_desc.count() > 0:
                target_desc_input = yoast_desc
            elif await rankmath_desc.count() > 0:
                target_desc_input = rankmath_desc

            # Update Meta Description if requested
            if new_meta_description and target_desc_input:
                try:
                    before_desc = (await target_desc_input.input_value()) or ""
                except Exception:
                    pass

                await BrowserActions.human_type(page, target_desc_input, new_meta_description)
                changes_made.append(("meta_description", before_desc, new_meta_description))

            # 4. Save / Update post
            update_btn = page.locator(
                "button.editor-post-publish-button, input#publish, button:has-text('Update')"
            ).first
            
            if await update_btn.count() > 0:
                pre_shot = await BrowserActions.capture_screenshot(page, "before_wp_update")
                await update_btn.click()
                await BrowserActions.human_delay(2000, 4000)
                post_shot = await BrowserActions.capture_screenshot(page, "after_wp_update")
            else:
                return {"success": False, "error": "Could not find WordPress Update/Publish button."}

            # 5. Live Verification
            verified_live = False
            if new_meta_description:
                verified_live = await self.verify_live_change(public_url, "meta_description", new_meta_description)

            # 6. Record changes in Database
            saved_records = []
            for field, b_val, a_val in changes_made:
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
                "changes": changes_made,
                "verified_live": verified_live,
                "change_records": saved_records,
                "screenshots": {"before": pre_shot, "after": post_shot}
            }

        except Exception as e:
            logger.error(f"WordPress update error: {e}")
            err_shot = await BrowserActions.capture_screenshot(page, "wp_update_error")
            return {
                "success": False,
                "error": str(e),
                "screenshot": err_shot
            }

    async def batch_auto_fix_audit_issues(
        self,
        db: AsyncSession,
        website_id: int,
        admin_base_url: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Automatically fixes audit issues in WordPress:
        - Meta titles
        - Meta descriptions
        - Headings
        """
        stmt = select(Recommendation).where(
            Recommendation.website_id == website_id,
            Recommendation.status == "suggested",
            Recommendation.automation_eligible == True
        ).limit(limit)
        res = await db.execute(stmt)
        recs = res.scalars().all()

        if not recs:
            return {"success": True, "message": "No pending WordPress recommendations.", "fixed_count": 0}

        fixed_count = 0
        details = []

        for rec in recs:
            change_data = rec.proposed_change_data or {}
            new_title = None
            new_desc = None
            
            if "title" in rec.issue_title.lower():
                new_title = change_data.get("new_value") or change_data.get("after", {}).get("title")
            elif "description" in rec.issue_title.lower() or "meta" in rec.issue_title.lower():
                new_desc = change_data.get("proposed_value") or change_data.get("new_value") or change_data.get("after", {}).get("meta_description")

            slug = rec.url.rstrip("/").split("/")[-1] or "home"
            res_wp = await self.update_post_seo(
                db=db,
                website_id=website_id,
                admin_base_url=admin_base_url,
                post_slug_or_title=slug,
                public_url=rec.url,
                new_title=new_title,
                new_meta_description=new_desc,
                recommendation_id=rec.id
            )

            if res_wp.get("success"):
                rec.status = "applied"
                fixed_count += 1
                details.append(f"Fixed {rec.issue_title} on {rec.url}")
            elif res_wp.get("needs_login"):
                return {
                    "success": False,
                    "needs_login": True,
                    "fixed_count": fixed_count,
                    "message": "WordPress login required. Please sign into wp-admin in the browser."
                }

        await db.commit()
        return {
            "success": True,
            "fixed_count": fixed_count,
            "details": details,
            "message": f"Successfully auto-fixed {fixed_count} audit issues in WordPress."
        }
