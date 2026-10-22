import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.database import AsyncSessionLocal
from ..models import Website, Task, AuditLog, Recommendation
from ..browser.controller import browser_controller
from ..crawler.spider import SEOSpider
from ..intelligence.keyword_research import KeywordResearcher
from ..intelligence.content_optimizer import ContentOptimizer
from ..workflows.gsc import GSCPerformanceAnalyzer, GSCSitemapsManager
from ..workflows.cms.wordpress import WordPressAutomation
from .queue import task_queue

logger = logging.getLogger("ai_seo.automation.scheduler")

class ContinuousSEOLoop:
    """
    Executes the 12-step autonomous loop for authorized websites in the background.
    Runs persistently even when Chrome Extension popup or tab is closed.
    Uses isolated sessions per step to prevent session cross-contamination and lazy-loading issues.
    """

    def __init__(self):
        self.is_running: bool = False
        self._loop_task: Optional[asyncio.Task] = None
        self.cycle_interval_seconds: int = 3600  # 1 hour between full site audits

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._loop_task = asyncio.create_task(self._run_loop())
            logger.info("Continuous SEO Loop started in background.")

    def stop(self):
        self.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
        logger.info("Continuous SEO Loop stopped.")

    async def _run_loop(self):
        while self.is_running:
            try:
                if not task_queue.is_paused:
                    # Retrieve active website IDs in a quick isolated session
                    async with AsyncSessionLocal() as db:
                        stmt = select(Website.id).where(Website.is_active == True)
                        res = await db.execute(stmt)
                        website_ids = res.scalars().all()

                    for wid in website_ids:
                        if task_queue.is_paused or not self.is_running:
                            break
                        await self.run_site_cycle(wid)

                # Wait before next cycle
                await asyncio.sleep(self.cycle_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous SEO cycle: {e}")
                await asyncio.sleep(60)

    async def run_site_cycle(self, website_id: int):
        """
        Executes one complete SEO audit & optimization pass for a website.
        """
        # Step 0: Extract website attributes into local variables
        async with AsyncSessionLocal() as db:
            stmt = select(Website).where(Website.id == website_id)
            res = await db.execute(stmt)
            site = res.scalar_one_or_none()
            if not site:
                return

            site_id = site.id
            site_domain = site.domain
            site_cms = site.cms_type
            site_admin_url = site.admin_url
            site_mode = site.automation_mode
            site_gsc_prop = site.gsc_property_id

        logger.info(f"Starting SEO pass for Website #{site_id} ({site_domain})")

        # Step 1: Run SEO Spider / Crawl in dedicated session
        crawl_results = []
        async with AsyncSessionLocal() as db:
            spider = SEOSpider(website_id=site_id, base_url=f"https://{site_domain}", max_pages=25)
            crawl_results = await spider.run(db)

        # Step 2: Content Optimization Recommendations
        async with AsyncSessionLocal() as db:
            optimizer = ContentOptimizer()
            recs = await optimizer.generate_recommendations_for_crawl(site_id, crawl_results, db)
            logger.info(f"Generated {len(recs)} optimization recommendations for {site_domain}")

        # Step 3: Check GSC Performance if property is configured
        if site_gsc_prop:
            try:
                analyzer = GSCPerformanceAnalyzer(browser_controller)
                nav_ok = await analyzer.navigate_to_performance(site_gsc_prop)
                if nav_ok.get("success"):
                    queries = await analyzer.extract_queries_table(max_rows=30)
                    async with AsyncSessionLocal() as db:
                        kw_researcher = KeywordResearcher()
                        await kw_researcher.analyze_gsc_queries(site_id, queries, db)
                    logger.info(f"Synced {len(queries)} GSC queries for {site_domain}")
            except Exception as e:
                logger.debug(f"GSC pass skipped or failed for {site_domain}: {e}")

        # Step 4: If Autonomous mode is enabled, execute low-risk meta description fixes
        if site_mode == "autonomous" and site_cms == "wordpress" and site_admin_url:
            async with AsyncSessionLocal() as db:
                stmt_rec = select(Recommendation).where(
                    Recommendation.website_id == site_id,
                    Recommendation.status == "suggested",
                    Recommendation.risk_level == "low",
                    Recommendation.automation_eligible == True
                ).limit(3)
                res_rec = await db.execute(stmt_rec)
                low_risk_recs = res_rec.scalars().all()

                wp = WordPressAutomation(browser_controller)
                for rec in low_risk_recs:
                    if task_queue.is_paused or not self.is_running:
                        break

                    change_data = rec.proposed_change_data or {}
                    new_desc = change_data.get("proposed_value")
                    if new_desc:
                        logger.info(f"Autonomous Mode: applying low-risk fix for {rec.url}")
                        res = await wp.update_post_seo(
                            db=db,
                            website_id=site_id,
                            admin_base_url=site_admin_url,
                            post_slug_or_title=rec.url.split("/")[-2] or rec.url.split("/")[-1],
                            public_url=rec.url,
                            new_meta_description=new_desc,
                            recommendation_id=rec.id
                        )
                        if res.get("success"):
                            rec.status = "applied"
                            task_queue.daily_actions_count += 1
                        else:
                            logger.warning(f"Failed to auto-apply fix: {res.get('error')}")

                await db.commit()

continuous_loop = ContinuousSEOLoop()
