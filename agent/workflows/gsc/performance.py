import asyncio
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from ...browser.controller import BrowserController
from ...browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.workflows.gsc.performance")

class GSCPerformanceAnalyzer:
    """
    Automates extracting real search performance data directly from
    Google Search Console's Performance Report browser interface.
    """

    def __init__(self, browser: BrowserController):
        self.browser = browser

    async def navigate_to_performance(self, property_id: str) -> Dict[str, Any]:
        """
        Navigates directly to the Performance report for the given property.
        Example property_id: 'sc-domain:example.com' or 'https://example.com/'
        """
        encoded_prop = quote(property_id, safe='')
        url = f"https://search.google.com/search-console/performance/search-analytics?resource_id={encoded_prop}"
        result = await self.browser.navigate(url, wait_until="networkidle")
        return result

    async def extract_metric_cards(self) -> Dict[str, Any]:
        """
        Extracts Total Clicks, Total Impressions, Average CTR, Average Position
        from the top scorecards in Search Console.
        """
        page = await self.browser.get_page()
        try:
            # Activate all metric scorecards by clicking their checkbox/cards if inactive
            cards = await page.query_selector_all("[role='tab'], [data-metric-type]")
            for card in cards:
                aria_selected = await card.get_attribute("aria-selected")
                if aria_selected == "false":
                    await card.click()
                    await asyncio.sleep(0.3)

            await BrowserActions.human_delay(500, 1000)

            # Extract metrics using page evaluation
            metrics = await page.evaluate("""() => {
                const getVal = (label) => {
                    // Search for card containing label text
                    const nodes = Array.from(document.querySelectorAll("[role='tab'], div"));
                    for (const n of nodes) {
                        if (n.innerText && n.innerText.includes(label)) {
                            const lines = n.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                            const labelIdx = lines.findIndex(l => l.includes(label));
                            if (labelIdx !== -1 && lines[labelIdx + 1]) {
                                return lines[labelIdx + 1];
                            }
                        }
                    }
                    return null;
                };

                return {
                    total_clicks: getVal('Total clicks') || getVal('Clicks') || '0',
                    total_impressions: getVal('Total impressions') || getVal('Impressions') || '0',
                    average_ctr: getVal('Average CTR') || getVal('CTR') || '0%',
                    average_position: getVal('Average position') || getVal('Position') || '0.0'
                };
            }""")
            return metrics
        except Exception as e:
            logger.warning(f"Error extracting metric cards: {e}")
            return {
                "total_clicks": "0",
                "total_impressions": "0",
                "average_ctr": "0%",
                "average_position": "0.0"
            }

    async def extract_queries_table(self, max_rows: int = 50) -> List[Dict[str, Any]]:
        """
        Extracts rows from the Queries report table in the browser UI.
        """
        page = await self.browser.get_page()
        rows = []
        try:
            # Ensure "Queries" tab is selected
            queries_tab = page.get_by_role("tab", name="QUERIES")
            if await queries_tab.count() > 0:
                await queries_tab.first.click()
                await BrowserActions.human_delay(400, 800)

            # Extract table rows
            table_data = await page.evaluate("""(maxCount) => {
                const results = [];
                const rows = document.querySelectorAll("table tbody tr");
                for (const row of rows) {
                    if (results.length >= maxCount) break;
                    const cols = Array.from(row.querySelectorAll("td")).map(c => c.innerText.trim());
                    if (cols.length >= 2) {
                        results.push({
                            query: cols[0] || '',
                            clicks: cols[1] || '0',
                            impressions: cols[2] || '0',
                            ctr: cols[3] || '0%',
                            position: cols[4] || '0.0'
                        });
                    }
                }
                return results;
            }""", max_rows)
            return table_data
        except Exception as e:
            logger.warning(f"Error extracting queries table: {e}")
            return []

    async def extract_pages_table(self, max_rows: int = 50) -> List[Dict[str, Any]]:
        """
        Extracts rows from the Pages report table in the browser UI.
        """
        page = await self.browser.get_page()
        try:
            # Click "Pages" tab
            pages_tab = page.get_by_role("tab", name="PAGES")
            if await pages_tab.count() > 0:
                await pages_tab.first.click()
                await BrowserActions.human_delay(500, 1000)

            table_data = await page.evaluate("""(maxCount) => {
                const results = [];
                const rows = document.querySelectorAll("table tbody tr");
                for (const row of rows) {
                    if (results.length >= maxCount) break;
                    const cols = Array.from(row.querySelectorAll("td")).map(c => c.innerText.trim());
                    if (cols.length >= 2) {
                        results.push({
                            url: cols[0] || '',
                            clicks: cols[1] || '0',
                            impressions: cols[2] || '0',
                            ctr: cols[3] || '0%',
                            position: cols[4] || '0.0'
                        });
                    }
                }
                return results;
            }""", max_rows)
            return table_data
        except Exception as e:
            logger.warning(f"Error extracting pages table: {e}")
            return []
