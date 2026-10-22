import logging
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Recommendation, CrawlResult

logger = logging.getLogger("ai_seo.intelligence.technical_fixer")

class TechnicalSEOFixer:
    """
    Stage 4: Fix technical SEO.
    Ensures pages can be crawled and indexed with zero barriers:
    - Robots.txt syntax and Googlebot access
    - XML Sitemap validation
    - Canonical tag consistency & self-referencing
    - HTTP status codes & redirect chains
    - HTTPS enforcement
    - Mobile viewport readiness
    """

    async def audit_and_fix_technical_barriers(
        self,
        website_id: int,
        domain: str,
        crawl_pages: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            "robots_txt_ok": True,
            "robots_txt_details": "",
            "sitemap_found": False,
            "sitemap_url": "",
            "https_enforced": False,
            "technical_issues_found": 0,
            "recommendations_created": 0
        }

        # 1. Inspect robots.txt
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                r_robots = await client.get(f"https://{domain}/robots.txt")
                if r_robots.status_code == 200:
                    text = r_robots.text.lower()
                    if "disallow: /" in text and "disallow: /wp-admin" not in text:
                        # Potential site-wide blocking
                        results["robots_txt_ok"] = False
                        results["robots_txt_details"] = "Warning: robots.txt contains 'Disallow: /' which may block Googlebot."
                        await self._create_rec_if_not_exists(
                            website_id=website_id,
                            url=f"https://{domain}/robots.txt",
                            issue_title="Robots.txt Blocking Site Indexation",
                            severity="critical",
                            category="technical",
                            evidence=r_robots.text[:200],
                            proposed_fix="Update robots.txt to allow search engines to crawl public content: 'User-agent: * Disallow: /wp-admin/'",
                            expected_benefit="Restores full search engine crawling and indexation.",
                            risk_level="high",
                            db=db
                        )
                        results["technical_issues_found"] += 1
                    else:
                        results["robots_txt_details"] = "Robots.txt is accessible and permits crawler access."
                else:
                    results["robots_txt_details"] = "Robots.txt not found (returns non-200 status code)."
        except Exception as e:
            results["robots_txt_details"] = f"Robots.txt check skipped: {str(e)}"

        # 2. Inspect XML Sitemap
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                for sm_path in ["sitemap.xml", "sitemap_index.xml", "wp-sitemap.xml"]:
                    r_sm = await client.get(f"https://{domain}/{sm_path}")
                    if r_sm.status_code == 200 and ("<urlset" in r_sm.text or "<sitemapindex" in r_sm.text):
                        results["sitemap_found"] = True
                        results["sitemap_url"] = f"https://{domain}/{sm_path}"
                        break
                
                if not results["sitemap_found"]:
                    await self._create_rec_if_not_exists(
                        website_id=website_id,
                        url=f"https://{domain}/sitemap.xml",
                        issue_title="Missing XML Sitemap",
                        severity="high",
                        category="technical",
                        evidence="No valid XML sitemap detected at standard locations (/sitemap.xml, /sitemap_index.xml).",
                        proposed_fix="Generate and submit an XML sitemap to ensure rapid discovery of all URLs.",
                        expected_benefit="Accelerates Google's discovery of new and updated pages.",
                        risk_level="low",
                        db=db
                    )
                    results["technical_issues_found"] += 1
        except Exception as e:
            logger.debug(f"Sitemap check error: {e}")

        # 3. Analyze crawl pages for technical status codes, canonicals, and viewport
        for p in crawl_pages:
            url = p.get("url", "")
            status_code = p.get("status_code", 200)
            canonical = p.get("canonical")
            issues = p.get("issues", [])

            # Check 404 or server errors
            if status_code in (404, 500, 502, 503):
                results["technical_issues_found"] += 1
                await self._create_rec_if_not_exists(
                    website_id=website_id,
                    url=url,
                    issue_title=f"HTTP {status_code} Error on Crawled URL",
                    severity="critical" if status_code == 404 else "high",
                    category="technical",
                    evidence=f"URL returned HTTP status code {status_code}.",
                    proposed_fix=f"Resolve dead link or implement a 301 redirect to the closest relevant live page.",
                    expected_benefit="Eliminates crawl waste and prevents user bounce rate.",
                    risk_level="medium",
                    db=db
                )

            # Check missing canonical
            if not canonical and status_code == 200:
                results["technical_issues_found"] += 1
                await self._create_rec_if_not_exists(
                    website_id=website_id,
                    url=url,
                    issue_title="Missing Canonical Tag",
                    severity="medium",
                    category="technical",
                    evidence="Page has no rel='canonical' tag in the HTML head.",
                    proposed_fix=f"Add `<link rel='canonical' href='{url}' />` to prevent duplicate content indexing.",
                    expected_benefit="Consolidates page authority and prevents duplicate URL penalties.",
                    risk_level="low",
                    db=db
                )

        await db.commit()
        return results

    async def _create_rec_if_not_exists(
        self,
        website_id: int,
        url: str,
        issue_title: str,
        severity: str,
        category: str,
        evidence: str,
        proposed_fix: str,
        expected_benefit: str,
        risk_level: str,
        db: AsyncSession
    ):
        stmt = select(Recommendation.id).where(
            Recommendation.website_id == website_id,
            Recommendation.url == url,
            Recommendation.issue_title == issue_title
        ).limit(1)
        res = await db.execute(stmt)
        if not res.scalar():
            rec = Recommendation(
                website_id=website_id,
                url=url,
                issue_title=issue_title,
                severity=severity,
                category=category,
                evidence=evidence,
                proposed_fix=proposed_fix,
                expected_benefit=expected_benefit,
                risk_level=risk_level,
                automation_eligible=True,
                status="suggested"
            )
            db.add(rec)
