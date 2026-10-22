import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions
from ...models import ChangeRecord, Recommendation

logger = logging.getLogger("ai_seo.workflows.cms.base")

class BaseCMSAutomation:
    """
    Abstract Base Class for CMS automated SEO modifications.
    Ensures that every change is captured, verified on the live site,
    and supports immediate single-click rollback.
    """

    def __init__(self, browser: BrowserController):
        self.browser = browser

    async def verify_live_change(
        self,
        public_url: str,
        expected_field: str,
        expected_value: str
    ) -> bool:
        """
        Fetches the live published URL and confirms that the modified SEO tag
        is actively serving the expected content in live HTML.
        """
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(public_url)
                if resp.status_code != 200:
                    logger.warning(f"Live verification: HTTP {resp.status_code} returned for {public_url}")
                    return False
                
                soup = BeautifulSoup(resp.text, "html.parser")
                if expected_field == "meta_description":
                    meta = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "description"})
                    content = meta.get("content", "").strip() if meta else ""
                    return expected_value.strip().lower() in content.lower()
                elif expected_field == "title":
                    title_tag = soup.find("title")
                    text = title_tag.get_text().strip() if title_tag else ""
                    return expected_value.strip().lower() in text.lower()
                
            return False
        except Exception as e:
            logger.error(f"Live verification error on {public_url}: {e}")
            return False

    async def record_change(
        self,
        db: AsyncSession,
        website_id: int,
        recommendation_id: Optional[int],
        url: str,
        field_name: str,
        before_val: str,
        after_val: str,
        status: str = "applied"
    ) -> ChangeRecord:
        """
        Records the exact before and after values for audit and rollback.
        """
        record = ChangeRecord(
            website_id=website_id,
            recommendation_id=recommendation_id,
            url=url,
            field_name=field_name,
            before_value=before_val,
            after_value=after_val,
            status=status,
            applied_at=datetime.now(timezone.utc)
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
