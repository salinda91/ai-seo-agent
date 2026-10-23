import asyncio
import re
import logging
from typing import Dict, Any, List, Set, Optional, Tuple
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.security import is_safe_url_for_crawling
from ..models import CrawlResult, Recommendation
from .analyzer import PageSEOAnalyzer

logger = logging.getLogger("ai_seo.crawler.spider")

def format_brand_name_from_domain(domain_part: str) -> str:
    s = domain_part.replace('-', ' ').replace('_', ' ')
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    if ' ' not in s:
        words = ['ocean', 'view', 'beach', 'resort', 'villas', 'villa', 'hotel', 'travel', 'tours', 'safari', 'kitesurf', 'labs', 'lab', 'tech', 'cloud', 'digital', 'global', 'solutions', 'live', 'life']
        pattern = '|'.join(words)
        spaced = re.sub(f'({pattern})', r' \1 ', s, flags=re.IGNORECASE)
        s = ' '.join(spaced.split())
    return s.title()

def synthesize_seo_recommendation(
    url: str,
    issue_type: str,
    page_title: Optional[str] = None,
    page_meta: Optional[str] = None,
    base_url: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Produces brand-appropriate, human-readable copy and structured change data
    for crawler-detected issues, preventing raw instruction strings or URLs
    from leaking into recommendations and code fixes.
    """
    parsed = urlparse(url)
    raw_path = parsed.path.strip("/")
    domain = (parsed.netloc or urlparse(base_url or "").netloc).replace("www.", "").split(":")[0]
    domain_part = domain.split(".")[0]
    brand = format_brand_name_from_domain(domain_part) if domain_part else "Website"

    slug_titles = {
        "": "Home",
        "stay": "Accommodations & Cabanas",
        "dine": "Dining & Local Flavours",
        "experiences": "Adventures & Experiences",
        "faq": "Frequently Asked Questions",
        "location": "Location & Directions",
        "offers": "Special Offers & Packages",
        "about": "About Us",
        "contact": "Contact Us",
        "privacy-policy": "Privacy Policy"
    }
    slug_clean = raw_path.lower()
    topic = slug_titles.get(slug_clean)
    if not topic:
        last_seg = slug_clean.split("/")[-1]
        topic = last_seg.replace("-", " ").replace("_", " ").title() if last_seg else brand

    if issue_type == "missing_h1":
        heading = f"Welcome to {brand}" if not slug_clean else topic
        return (
            f"Ensure page has a clear H1 heading: '{heading}'",
            {"field": "h1", "proposed_value": heading}
        )
    elif issue_type in ("missing_meta_description", "long_meta_description", "short_meta_description"):
        desc = f"Discover {topic} at {brand}. Explore our authentic offerings, services, and experiences."
        return (
            f"Update meta description to: '{desc}'",
            {"field": "meta_description", "proposed_value": desc}
        )
    elif issue_type in ("missing_title", "long_title", "short_title"):
        title = f"{topic} | {brand}"
        return (
            f"Update title to: '{title}'",
            {"field": "title", "proposed_value": title}
        )
    elif issue_type == "missing_canonical":
        return (
            f"Add canonical link pointing to '{url}'",
            {"field": "canonical", "proposed_value": url}
        )
    elif issue_type == "images_missing_alt":
        alt = f"{topic} photo"
        return (
            f"Add descriptive alt text such as '{alt}' to images",
            {"field": "image_alt", "proposed_value": alt}
        )
    elif issue_type == "missing_structured_data":
        schema_json = f'{{\n  "@context": "https://schema.org",\n  "@type": "WebPage",\n  "name": "{topic}",\n  "url": "{url}"\n}}'
        return (
            "Add Schema.org WebPage structured data.",
            {"field": "schema_org", "proposed_value": schema_json}
        )

    return (
        f"Resolve {issue_type} on {url}.",
        {"field": issue_type, "proposed_value": None}
    )

class SEOSpider:
    """
    Polite asynchronous website crawler.
    Discovers URLs via sitemaps and internal links.
    Guarantees SSRF protection and stores on-page SEO audits.
    """

    def __init__(
        self,
        website_id: int,
        base_url: str,
        max_pages: int = 50,
        concurrency: int = 3,
        request_delay: float = 0.5
    ):
        self.website_id = website_id
        self.base_url = base_url.rstrip("/")
        self.domain = urlparse(base_url).netloc.lower()
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.request_delay = request_delay
        
        self.visited: Set[str] = set()
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.results: List[Dict[str, Any]] = []

    async def run(self, db: AsyncSession) -> List[Dict[str, Any]]:
        logger.info(f"Starting SEO crawl for {self.base_url} (max pages: {self.max_pages})")
        
        # 1. Discover sitemap from robots.txt or standard paths
        sitemap_urls = await self._discover_sitemap_urls()
        for s_url in sitemap_urls:
            await self.queue.put(s_url)

        # 2. Add base URL to queue
        if self.base_url not in self.visited:
            await self.queue.put(self.base_url)

        semaphore = asyncio.Semaphore(self.concurrency)
        client = httpx.AsyncClient(
            headers={"User-Agent": "AI-SEO-Auditor/1.0 (+https://github.com/ai-seo)"},
            timeout=15.0,
            follow_redirects=True,
            verify=True
        )

        try:
            async def worker():
                while not self.queue.empty() and len(self.visited) < self.max_pages:
                    try:
                        url = await self.queue.get()
                    except asyncio.QueueEmpty:
                        break

                    if url in self.visited:
                        self.queue.task_done()
                        continue

                    # Validate SSRF safety
                    is_safe, reason = is_safe_url_for_crawling(url)
                    if not is_safe:
                        logger.warning(f"Skipping unsafe URL {url}: {reason}")
                        self.queue.task_done()
                        continue

                    self.visited.add(url)

                    async with semaphore:
                        await asyncio.sleep(self.request_delay)
                        page_data = await self._fetch_and_analyze(client, url)
                        if page_data:
                            self.results.append(page_data)

                            # Enqueue discovered internal links
                            for next_link in page_data.get("internal_links", []):
                                if (
                                    next_link not in self.visited
                                    and urlparse(next_link).netloc.lower() == self.domain
                                    and self.queue.qsize() < (self.max_pages * 2)
                                ):
                                    await self.queue.put(next_link)

                    self.queue.task_done()

            # Run workers
            tasks = [asyncio.create_task(worker()) for _ in range(self.concurrency)]
            await asyncio.gather(*tasks)

            # Batch save all crawled results & recommendations cleanly
            await self._save_all_results(db)

        finally:
            await client.aclose()

        logger.info(f"Finished crawl for {self.base_url}. Inspected {len(self.results)} pages.")
        return self.results

    async def _fetch_and_analyze(self, client: httpx.AsyncClient, url: str) -> Optional[Dict[str, Any]]:
        try:
            resp = await client.get(url)
            content_type = resp.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                logger.debug(f"Skipping non-HTML resource: {url} ({content_type})")
                return None

            analyzed = PageSEOAnalyzer.analyze(url, resp.text, resp.status_code)
            return analyzed
        except Exception as e:
            logger.warning(f"Error crawling {url}: {e}")
            return {
                "url": url,
                "status_code": 0,
                "title": "",
                "meta_description": "",
                "h1": "",
                "canonical": "",
                "robots_meta": "",
                "internal_links": [],
                "external_links": [],
                "internal_links_count": 0,
                "external_links_count": 0,
                "images_without_alt": 0,
                "issues": [{"severity": "critical", "type": "connection_error", "message": f"Failed to fetch page: {str(e)}"}]
            }

    async def _discover_sitemap_urls(self) -> List[str]:
        """Discovers URLs from robots.txt or common sitemap locations."""
        discovered = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                # 1. Try robots.txt
                robots_url = f"{self.base_url}/robots.txt"
                is_safe, _ = is_safe_url_for_crawling(robots_url)
                if is_safe:
                    try:
                        r = await client.get(robots_url)
                        if r.status_code == 200:
                            for line in r.text.splitlines():
                                if line.lower().startswith("sitemap:"):
                                    s_url = line.split(":", 1)[1].strip()
                                    discovered.extend(await self._parse_xml_sitemap(client, s_url))
                    except Exception:
                        pass

                # 2. Try standard sitemap.xml if none found yet
                if not discovered:
                    std_sitemap = f"{self.base_url}/sitemap.xml"
                    is_safe, _ = is_safe_url_for_crawling(std_sitemap)
                    if is_safe:
                        discovered.extend(await self._parse_xml_sitemap(client, std_sitemap))

        except Exception as e:
            logger.debug(f"Sitemap discovery note: {e}")
        return discovered[:self.max_pages]

    async def _parse_xml_sitemap(self, client: httpx.AsyncClient, sitemap_url: str) -> List[str]:
        urls = []
        try:
            r = await client.get(sitemap_url)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                # Handle sitemap index or standard urlset
                for elem in root.iter():
                    if elem.tag.endswith("loc") and elem.text:
                        loc = elem.text.strip()
                        if loc.endswith(".xml"):
                            # nested sitemap
                            urls.extend(await self._parse_xml_sitemap(client, loc))
                        else:
                            urls.append(loc)
                    if len(urls) >= self.max_pages:
                        break
        except Exception:
            pass
        return urls

    async def _save_all_results(self, db: AsyncSession):
        """Persists all CrawlResult items and auto-generates Recommendations cleanly."""
        try:
            for data in self.results:
                crawl_res = CrawlResult(
                    website_id=self.website_id,
                    url=data["url"],
                    status_code=data.get("status_code", 200),
                    title=data.get("title"),
                    meta_description=data.get("meta_description"),
                    h1=data.get("h1"),
                    canonical=data.get("canonical"),
                    robots_meta=data.get("robots_meta"),
                    internal_links_count=data.get("internal_links_count", 0),
                    external_links_count=data.get("external_links_count", 0),
                    images_without_alt=data.get("images_without_alt", 0),
                    issues=data.get("issues", [])
                )
                db.add(crawl_res)

                # Create Recommendations for issues
                for issue in data.get("issues", []):
                    risk = "low"
                    if issue.get("severity") == "critical":
                        risk = "medium"

                    fix_desc, change_data = synthesize_seo_recommendation(
                        url=data["url"],
                        issue_type=issue.get("type", "SEO Issue"),
                        page_title=data.get("title"),
                        page_meta=data.get("meta_description"),
                        base_url=self.base_url
                    )

                    # Safe check for existing recommendation (avoids MultipleResultsFound)
                    stmt_rec = select(Recommendation.id).where(
                        Recommendation.website_id == self.website_id,
                        Recommendation.url == data["url"],
                        Recommendation.issue_title == issue.get("type", "SEO Issue")
                    ).limit(1)
                    res_rec = await db.execute(stmt_rec)
                    if not res_rec.scalar():
                        rec = Recommendation(
                            website_id=self.website_id,
                            url=data["url"],
                            issue_title=issue.get("type", "SEO Issue"),
                            severity=issue.get("severity", "medium"),
                            category="onpage" if "title" in issue.get("type", "") or "meta" in issue.get("type", "") else "technical",
                            evidence=issue.get("message", ""),
                            proposed_fix=fix_desc,
                            proposed_change_data=change_data,
                            risk_level=risk,
                            automation_eligible=True,
                            status="suggested"
                        )
                        db.add(rec)

            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save crawl results to database: {e}")
            await db.rollback()
            await db.rollback()
