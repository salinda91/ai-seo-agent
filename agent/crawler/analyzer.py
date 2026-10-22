import json
from typing import Dict, Any, List, Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from ..core.security import sanitize_untrusted_text

class PageSEOAnalyzer:
    """
    Parses and audits a page's HTML for key on-page SEO factors.
    Treats all incoming HTML/text as untrusted data.
    """

    @staticmethod
    def analyze(url: str, html: str, status_code: int = 200) -> Dict[str, Any]:
        issues = []
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(url).netloc.lower()

        # 1. Title Tag
        title_el = soup.find("title")
        raw_title = title_el.get_text().strip() if title_el else ""
        title = sanitize_untrusted_text(raw_title, 300)
        
        if not title:
            issues.append({"severity": "critical", "type": "missing_title", "message": "Missing <title> tag."})
        elif len(title) < 20:
            issues.append({"severity": "medium", "type": "short_title", "message": f"Title too short ({len(title)} chars). Recommended: 40-60 chars."})
        elif len(title) > 65:
            issues.append({"severity": "low", "type": "long_title", "message": f"Title may truncate in SERPs ({len(title)} chars). Recommended: 40-60 chars."})

        # 2. Meta Description
        meta_desc_el = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "description"})
        raw_desc = meta_desc_el.get("content", "").strip() if meta_desc_el else ""
        meta_description = sanitize_untrusted_text(raw_desc, 600)
        
        if not meta_description:
            issues.append({"severity": "high", "type": "missing_meta_description", "message": "Missing meta description."})
        elif len(meta_description) < 70:
            issues.append({"severity": "medium", "type": "short_meta_description", "message": f"Meta description is short ({len(meta_description)} chars). Ideal: 120-160 chars."})
        elif len(meta_description) > 165:
            issues.append({"severity": "low", "type": "long_meta_description", "message": f"Meta description exceeds SERP display limit ({len(meta_description)} chars)."})

        # 3. Headings (H1, H2, H3)
        h1_tags = soup.find_all("h1")
        h1_text = sanitize_untrusted_text(h1_tags[0].get_text().strip()) if h1_tags else ""
        if len(h1_tags) == 0:
            issues.append({"severity": "high", "type": "missing_h1", "message": "Page has no <h1> heading."})
        elif len(h1_tags) > 1:
            issues.append({"severity": "medium", "type": "multiple_h1", "message": f"Page has multiple ({len(h1_tags)}) <h1> headings. Usually recommend exactly one per page."})

        # 4. Canonical Tag
        canonical_el = soup.find("link", rel=lambda x: x and "canonical" in x.lower())
        canonical = canonical_el.get("href", "").strip() if canonical_el else ""
        if not canonical:
            issues.append({"severity": "medium", "type": "missing_canonical", "message": "Missing rel=canonical link tag."})

        # 5. Robots Meta
        robots_el = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "robots"})
        robots_meta = robots_el.get("content", "").strip() if robots_el else ""
        if "noindex" in robots_meta.lower():
            issues.append({"severity": "critical", "type": "noindex_present", "message": "Page contains 'noindex' directive in meta robots."})

        # 6. Viewport / Mobile
        viewport_el = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "viewport"})
        if not viewport_el:
            issues.append({"severity": "high", "type": "missing_viewport", "message": "Missing responsive viewport meta tag."})

        # 7. Images and Alt Attributes
        images = soup.find_all("img")
        images_without_alt = 0
        for img in images:
            alt = img.get("alt")
            if alt is None or not alt.strip():
                images_without_alt += 1
        
        if images_without_alt > 0:
            issues.append({
                "severity": "medium",
                "type": "images_missing_alt",
                "message": f"{images_without_alt} images missing alt text."
            })

        # 8. Links Extraction
        internal_links: Set[str] = set()
        external_links: Set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(url, href)
            parsed_link = urlparse(full_url)
            if parsed_link.scheme in ("http", "https"):
                # Clean fragments
                cleaned_url = parsed_link._replace(fragment="").geturl()
                if parsed_link.netloc.lower() == base_domain:
                    internal_links.add(cleaned_url)
                else:
                    external_links.add(cleaned_url)

        # 9. Structured Data (JSON-LD)
        has_schema = False
        schemas = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                schemas.append(data.get("@type", "Unknown"))
                has_schema = True
            except Exception:
                pass

        if not has_schema:
            issues.append({"severity": "low", "type": "missing_structured_data", "message": "No JSON-LD structured data detected."})

        # 10. Thin Content Check
        body = soup.find("body")
        word_count = len(body.get_text().split()) if body else 0
        if word_count < 150:
            issues.append({"severity": "high", "type": "thin_content", "message": f"Low word count ({word_count} words). May be considered thin content."})

        return {
            "url": url,
            "status_code": status_code,
            "title": title,
            "meta_description": meta_description,
            "h1": h1_text,
            "canonical": canonical,
            "robots_meta": robots_meta,
            "internal_links": list(internal_links),
            "external_links": list(external_links),
            "internal_links_count": len(internal_links),
            "external_links_count": len(external_links),
            "images_count": len(images),
            "images_without_alt": images_without_alt,
            "schemas": schemas,
            "word_count": word_count,
            "issues": issues
        }
