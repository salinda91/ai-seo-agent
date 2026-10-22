import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("ai_seo.browser.inspector")

class PageInspector:
    """
    Inspects DOM structure, accessibility labels, visible text, interactive elements,
    and forms using stable selectors and accessible roles.
    """

    @staticmethod
    async def get_page_summary(page) -> Dict[str, Any]:
        """
        Gathers comprehensive page state: title, URL, headings, interactive elements count.
        """
        title = await page.title()
        url = page.url
        
        # Extract headings and metadata
        seo_meta = await page.evaluate("""() => {
            const getMeta = (name) => {
                const el = document.querySelector(`meta[name='${name}'], meta[property='${name}']`);
                return el ? el.getAttribute('content') : null;
            };
            const headings = [];
            document.querySelectorAll('h1, h2, h3').forEach(h => {
                if (headings.length < 30) {
                    headings.push({ tag: h.tagName.toLowerCase(), text: h.innerText.trim().slice(0, 150) });
                }
            });
            const canonical = document.querySelector("link[rel='canonical']")?.getAttribute('href') || null;
            return {
                title: document.title,
                description: getMeta('description'),
                robots: getMeta('robots'),
                canonical: canonical,
                headings: headings
            };
        }""")

        return {
            "url": url,
            "title": title,
            "seo_meta": seo_meta
        }

    @staticmethod
    async def extract_interactive_elements(page) -> List[Dict[str, Any]]:
        """
        Finds actionable buttons, links, inputs, and select elements with their stable selectors,
        accessible names, text content, and bounding boxes.
        """
        elements = await page.evaluate("""() => {
            const results = [];
            const isVisible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' && 
                       rect.width > 0 && 
                       rect.height > 0;
            };

            const query = "button, a[href], input, textarea, select, [role='button'], [role='tab'], [role='menuitem'], [role='checkbox'], [contenteditable='true']";
            const nodes = document.querySelectorAll(query);

            for (const el of nodes) {
                if (results.length >= 100) break; // Limit snapshot size
                if (!isVisible(el)) continue;

                const rect = el.getBoundingClientRect();
                const role = el.getAttribute('role') || el.tagName.toLowerCase();
                const ariaLabel = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || '';
                const name = el.getAttribute('name') || '';
                const id = el.id || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const text = (el.innerText || el.value || '').trim().slice(0, 80);

                // Build stable selector
                let selector = '';
                if (id && !id.match(/\\d{4,}/)) {
                    selector = `#${id}`;
                } else if (name) {
                    selector = `${el.tagName.toLowerCase()}[name='${name}']`;
                } else if (ariaLabel) {
                    selector = `${el.tagName.toLowerCase()}[aria-label='${ariaLabel}']`;
                } else if (el.tagName.toLowerCase() === 'a' && el.getAttribute('href')) {
                    const href = el.getAttribute('href');
                    if (href.startsWith('http') || href.startsWith('/')) {
                        selector = `a[href='${href.slice(0, 50)}']`;
                    }
                }

                results.push({
                    tagName: el.tagName.toLowerCase(),
                    role: role,
                    text: text,
                    ariaLabel: ariaLabel,
                    name: name,
                    id: id,
                    placeholder: placeholder,
                    type: el.getAttribute('type') || '',
                    selector: selector,
                    bbox: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    }
                });
            }
            return results;
        }""")
        return elements

    @staticmethod
    async def find_element_by_accessible_name(page, role: str, name: str):
        """
        Locates Playwright Locator by accessible role and name (preferred strategy).
        """
        try:
            locator = page.get_by_role(role, name=name, exact=False)
            count = await locator.count()
            if count > 0:
                return locator.first
        except Exception:
            pass
        return None

    @staticmethod
    async def find_input_by_label_or_placeholder(page, label_or_placeholder: str):
        """
        Finds input fields by visible label or placeholder.
        """
        try:
            by_label = page.get_by_label(label_or_placeholder, exact=False)
            if await by_label.count() > 0:
                return by_label.first
        except Exception:
            pass
        try:
            by_placeholder = page.get_by_placeholder(label_or_placeholder, exact=False)
            if await by_placeholder.count() > 0:
                return by_placeholder.first
        except Exception:
            pass
        return None
