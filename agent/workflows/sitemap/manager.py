import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models import Website, CrawlResult, Recommendation, ChangeRecord
from ...workflows.codebase.git_fixer import local_codebase_fixer
from ...workflows.gsc import GSCSitemapsManager
from ...browser.controller import browser_controller

logger = logging.getLogger("ai_seo.workflows.sitemap.manager")

class SitemapManager:
    """
    Automates XML sitemap availability checking, sitemap XML generation,
    file deployment to local codebase with Git commit/push, and submission to
    Google Search Console via browser automation.
    """

    CANDIDATE_PATHS = ["sitemap.xml", "sitemap_index.xml", "wp-sitemap.xml"]

    async def check_sitemap_live(self, domain: str) -> Dict[str, Any]:
        """
        Inspects whether an XML sitemap is live and publicly accessible on the website.
        """
        clean_domain = domain.lower().replace("http://", "").replace("https://", "").strip("/")
        base_url = f"https://{clean_domain}"
        
        last_status = 404
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            for sm_path in self.CANDIDATE_PATHS:
                target_url = f"{base_url}/{sm_path}"
                try:
                    r = await client.get(target_url)
                    last_status = r.status_code
                    if r.status_code == 200:
                        text_lower = r.text.lower()
                        if "<urlset" in text_lower or "<sitemapindex" in text_lower:
                            return {
                                "available": True,
                                "sitemap_url": target_url,
                                "status_code": 200,
                                "details": f"Valid XML sitemap detected at {sm_path}."
                            }
                except Exception as e:
                    logger.debug(f"Error checking {target_url}: {e}")

        return {
            "available": False,
            "sitemap_url": f"{base_url}/sitemap.xml",
            "status_code": last_status,
            "details": f"No valid XML sitemap detected at standard locations (checked {', '.join(self.CANDIDATE_PATHS)})."
        }

    async def collect_urls(self, website: Website, db: AsyncSession) -> List[str]:
        """
        Collects all indexable public URLs for the website from crawl history
        and local codebase templates.
        """
        clean_domain = website.domain.lower().replace("http://", "").replace("https://", "").strip("/")
        base_url = f"https://{clean_domain}"
        urls = {f"{base_url}/"}

        # 1. Fetch discovered 200 OK pages from crawl_results table
        stmt_crawl = select(CrawlResult.url).where(
            CrawlResult.website_id == website.id,
            CrawlResult.status_code == 200
        )
        res_crawl = await db.execute(stmt_crawl)
        for u in res_crawl.scalars().all():
            if u:
                norm = u.strip()
                if norm.startswith(base_url) and not self._is_asset_or_admin_url(norm):
                    urls.add(norm.rstrip("/") if norm != f"{base_url}/" else norm)

        # 2. Extract public routes from local codebase if connected
        if website.local_repo_path:
            repo_path = Path(website.local_repo_path)
            if repo_path.exists() and repo_path.is_dir():
                discovered_slugs = self._scan_repo_for_routes(repo_path)
                for slug in discovered_slugs:
                    clean_slug = slug.strip("/")
                    if clean_slug:
                        urls.add(f"{base_url}/{clean_slug}")

        # Ensure base URL is included and return sorted list
        url_list = sorted(list(urls), key=lambda x: (x != f"{base_url}/", x))
        return url_list

    def _is_asset_or_admin_url(self, url: str) -> bool:
        """Filters out non-HTML static assets and private administrative routes."""
        path = urlparse(url).path.lower()
        static_exts = (
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
            ".css", ".js", ".json", ".xml", ".txt", ".pdf", ".zip"
        )
        if any(path.endswith(ext) for ext in static_exts):
            return True
        admin_patterns = ["/admin", "/login", "/dashboard", "/api/", "/wp-admin", "/checkout", "/cart"]
        if any(p in path for p in admin_patterns):
            return True
        return False

    def _scan_repo_for_routes(self, repo_path: Path) -> List[str]:
        """Scans repository files to discover public page routes."""
        slugs = set()
        
        # Candidate search directories
        search_dirs = [
            repo_path / "resources" / "js" / "pages",
            repo_path / "resources" / "views",
            repo_path / "pages",
            repo_path / "app",
            repo_path / "src" / "pages"
        ]

        # Common page file naming pattern (e.g. StayPage.jsx -> stay, DinePage.jsx -> dine)
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for f in sdir.rglob("*"):
                if f.is_file() and f.suffix in [".jsx", ".tsx", ".blade.php", ".html", ".vue"]:
                    # Ignore components, layouts, error pages, auth
                    name_lower = f.stem.lower()
                    if any(ign in name_lower for ign in ["layout", "modal", "card", "nav", "header", "footer", "auth", "login", "admin", "404", "500", "error", "component"]):
                        continue

                    # Clean slug
                    slug = name_lower.replace("page", "").strip("-_")
                    if slug in ["welcome", "index", "home"]:
                        continue
                    if slug:
                        slugs.add(slug)

        return list(slugs)

    def generate_sitemap_xml(self, urls: List[str], domain: str) -> str:
        """
        Generates standard sitemaps.org compliant XML string.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        clean_domain = domain.lower().replace("http://", "").replace("https://", "").strip("/")
        base_url = f"https://{clean_domain}/"

        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]

        for url in urls:
            clean_url = url.strip()
            is_root = (clean_url == base_url or clean_url == f"https://{clean_domain}")
            priority = "1.0" if is_root else "0.8"
            changefreq = "daily" if is_root else "weekly"

            xml_lines.append("  <url>")
            xml_lines.append(f"    <loc>{clean_url}</loc>")
            xml_lines.append(f"    <lastmod>{today}</lastmod>")
            xml_lines.append(f"    <changefreq>{changefreq}</changefreq>")
            xml_lines.append(f"    <priority>{priority}</priority>")
            xml_lines.append("  </url>")

        xml_lines.append("</urlset>\n")
        return "\n".join(xml_lines)

    async def deploy_sitemap_to_codebase(
        self,
        repo_path: Path,
        domain: str,
        xml_content: str,
        git_branch: str = "main",
        git_remote: str = "origin"
    ) -> Dict[str, Any]:
        """
        Writes sitemap.xml to the web root or public folder, ensures robots.txt references it,
        and commits and pushes to Git.
        """
        repo_path = repo_path.resolve()
        
        # Determine public target folder
        public_dir = repo_path / "public"
        target_dir = public_dir if public_dir.exists() and public_dir.is_dir() else repo_path
        
        sitemap_file = target_dir / "sitemap.xml"
        robots_file = target_dir / "robots.txt"

        # 1. Write sitemap.xml
        sitemap_file.write_text(xml_content, encoding="utf-8")
        rel_sitemap = str(sitemap_file.relative_to(repo_path))
        modified_files = [rel_sitemap]

        # 2. Ensure robots.txt links to the sitemap
        sitemap_directive = f"Sitemap: https://{domain}/sitemap.xml"
        if robots_file.exists():
            robots_content = robots_file.read_text(encoding="utf-8", errors="replace")
            if "sitemap:" not in robots_content.lower():
                robots_content = robots_content.rstrip() + f"\n\n{sitemap_directive}\n"
                robots_file.write_text(robots_content, encoding="utf-8")
                modified_files.append(str(robots_file.relative_to(repo_path)))
        else:
            default_robots = f"User-agent: *\nAllow: /\n\n{sitemap_directive}\n"
            robots_file.write_text(default_robots, encoding="utf-8")
            modified_files.append(str(robots_file.relative_to(repo_path)))

        # 3. Git Stage, Commit, and Push
        commit_sha = ""
        pushed = False
        push_message = ""

        val = await local_codebase_fixer.validate_repo(str(repo_path))
        if val.get("is_git"):
            for mf in modified_files:
                await local_codebase_fixer.run_git_command(repo_path, ["add", mf])

            commit_msg = f"feat(seo): create XML sitemap and update robots.txt\n\nAdded {rel_sitemap} with search-engine discovery directives."
            c_code, c_out, c_err = await local_codebase_fixer.run_git_command(repo_path, ["commit", "-m", commit_msg])
            if c_code == 0:
                _, sha_out, _ = await local_codebase_fixer.run_git_command(repo_path, ["rev-parse", "--short", "HEAD"])
                commit_sha = sha_out.strip()
                logger.info(f"Committed sitemap to Git ({commit_sha})")

                # Git Push
                if val.get("remote_url"):
                    p_code, p_out, p_err = await local_codebase_fixer.run_git_command(repo_path, ["push", git_remote or "origin", git_branch or "main"])
                    if p_code == 0:
                        pushed = True
                        push_message = f"Pushed sitemap commit {commit_sha} to {git_remote}/{git_branch}."
                    else:
                        push_message = f"Committed locally ({commit_sha}), push encountered: {p_err or p_out}"
            else:
                commit_sha = "already-up-to-date"

        return {
            "success": True,
            "target_file": rel_sitemap,
            "commit_sha": commit_sha,
            "pushed": pushed,
            "push_message": push_message
        }

    async def create_and_upload_sitemap(
        self,
        website_id: int,
        db: AsyncSession,
        auto_submit_gsc: bool = True
    ) -> Dict[str, Any]:
        """
        Complete end-to-end pipeline:
        1. Collects all indexable URLs
        2. Generates XML sitemap
        3. Deploys to codebase / web root and pushes to Git
        4. Submits sitemap in Google Search Console via browser controller
        5. Updates database recommendation and audit trail
        """
        stmt = select(Website).where(Website.id == website_id)
        res = await db.execute(stmt)
        site = res.scalar_one_or_none()
        if not site:
            return {"success": False, "error": "Website not found."}

        clean_domain = site.domain.lower().replace("http://", "").replace("https://", "").strip("/")
        
        # 1. Collect indexable URLs
        urls = await self.collect_urls(site, db)
        if not urls:
            urls = [f"https://{clean_domain}/"]

        # 2. Generate XML
        xml_content = self.generate_sitemap_xml(urls, clean_domain)
        sitemap_url = f"https://{clean_domain}/sitemap.xml"

        # 3. Deploy to local codebase
        deploy_res = {"success": True, "target_file": "sitemap.xml", "commit_sha": "", "pushed": False}
        if site.local_repo_path:
            deploy_res = await self.deploy_sitemap_to_codebase(
                repo_path=Path(site.local_repo_path),
                domain=clean_domain,
                xml_content=xml_content,
                git_branch=site.git_branch or "main",
                git_remote=site.git_remote or "origin"
            )

        # 4. Submit to GSC if enabled
        gsc_submitted = False
        gsc_message = ""
        if auto_submit_gsc and browser_controller.is_running:
            try:
                prop_id = site.gsc_property_id or f"sc-domain:{clean_domain}"
                mgr = GSCSitemapsManager(browser_controller)
                await mgr.navigate_to_sitemaps(prop_id)
                sub_res = await mgr.submit_sitemap("sitemap.xml")
                gsc_submitted = sub_res.get("success", False)
                gsc_message = sub_res.get("message", "Submitted in GSC UI.")
            except Exception as e:
                logger.warning(f"GSC submission note: {e}")
                gsc_message = f"GSC submission note: {e}"

        # 5. Resolve any pending 'Missing XML Sitemap' recommendation in DB
        stmt_rec = select(Recommendation).where(
            Recommendation.website_id == site.id,
            Recommendation.issue_title == "Missing XML Sitemap"
        )
        res_rec = await db.execute(stmt_rec)
        for r in res_rec.scalars().all():
            r.status = "applied"

        # 6. Add ChangeRecord
        change = ChangeRecord(
            website_id=site.id,
            url=sitemap_url,
            field_name="sitemap.xml",
            before_value="missing",
            after_value=f"{len(urls)} URLs indexed in {deploy_res.get('target_file', 'sitemap.xml')}",
            status="applied"
        )
        db.add(change)
        await db.commit()

        summary_msg = f"Generated XML sitemap with {len(urls)} URLs and saved to {deploy_res.get('target_file', 'sitemap.xml')}."
        if deploy_res.get("pushed"):
            summary_msg += " Committed and pushed to Git remote."
        if gsc_submitted:
            summary_msg += " Submitted to Google Search Console."

        return {
            "success": True,
            "message": summary_msg,
            "sitemap_url": sitemap_url,
            "urls_count": len(urls),
            "urls": urls[:20],
            "target_file": deploy_res.get("target_file"),
            "commit_sha": deploy_res.get("commit_sha"),
            "pushed_to_git": deploy_res.get("pushed"),
            "gsc_submitted": gsc_submitted,
            "gsc_message": gsc_message
        }

sitemap_manager = SitemapManager()
