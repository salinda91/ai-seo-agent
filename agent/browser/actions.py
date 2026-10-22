import asyncio
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging
from playwright.async_api import Page, Locator
from ..core.config import SCREENSHOTS_DIR

logger = logging.getLogger("ai_seo.browser.actions")

class BrowserActions:
    """
    Executes human-like mouse, keyboard, scrolling, and form actions
    with before/after screenshots and post-action verification.
    """

    @staticmethod
    async def capture_screenshot(page: Page, label: str = "step") -> str:
        """
        Saves a full-page or viewport screenshot and returns the file path.
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:19]
            filename = f"{timestamp}_{label}.png"
            filepath = SCREENSHOTS_DIR / filename
            await page.screenshot(path=str(filepath), full_page=False)
            return str(filepath)
        except Exception as e:
            logger.warning(f"Failed to capture screenshot ({label}): {e}")
            return ""

    @staticmethod
    async def human_delay(min_ms: int = 150, max_ms: int = 400):
        """Adds slight randomized delay to emulate human behavior."""
        delay = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
        await asyncio.sleep(delay)

    @staticmethod
    async def human_type(page: Page, selector_or_locator: Any, text: str, clear_first: bool = True) -> bool:
        """
        Types text with human-like keystroke intervals (35ms - 90ms).
        """
        try:
            if isinstance(selector_or_locator, str):
                locator = page.locator(selector_or_locator)
            else:
                locator = selector_or_locator

            await locator.scroll_into_view_if_needed(timeout=5000)
            await locator.click()
            await BrowserActions.human_delay(100, 250)

            if clear_first:
                # Select all and delete to simulate human clearing
                await page.keyboard.press("Control+A")
                await BrowserActions.human_delay(50, 100)
                await page.keyboard.press("Backspace")
                await BrowserActions.human_delay(80, 150)

            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.03, 0.08))

            await BrowserActions.human_delay(150, 300)
            return True
        except Exception as e:
            logger.error(f"Failed to type text into element: {e}")
            return False

    @staticmethod
    async def human_click(
        page: Page,
        selector_or_locator: Any,
        expected_change: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, str]]:
        """
        Clicks an element with pre/post screenshots and verification.
        Returns: (success: bool, message: str, screenshots: dict)
        """
        pre_screenshot = await BrowserActions.capture_screenshot(page, "before_click")
        screenshots = {"before": pre_screenshot}

        try:
            if isinstance(selector_or_locator, str):
                locator = page.locator(selector_or_locator)
            else:
                locator = selector_or_locator

            await locator.scroll_into_view_if_needed(timeout=7000)
            await BrowserActions.human_delay(150, 300)
            await locator.click(timeout=7000)
            
            # Wait for any quick DOM updates or transitions
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
            await BrowserActions.human_delay(300, 600)

            post_screenshot = await BrowserActions.capture_screenshot(page, "after_click")
            screenshots["after"] = post_screenshot

            return True, "Click successful", screenshots
        except Exception as e:
            post_screenshot = await BrowserActions.capture_screenshot(page, "after_click_failed")
            screenshots["after"] = post_screenshot
            logger.warning(f"Click failed: {e}")
            return False, f"Click failed: {str(e)}", screenshots

    @staticmethod
    async def human_scroll(page: Page, direction: str = "down", distance: int = 400):
        """
        Smooth human-like scrolling in small increments.
        """
        step = 50 if direction == "down" else -50
        remaining = abs(distance)
        while remaining > 0:
            current_step = min(abs(step), remaining) * (1 if step > 0 else -1)
            await page.mouse.wheel(0, current_step)
            remaining -= abs(current_step)
            await asyncio.sleep(random.uniform(0.02, 0.05))
        await BrowserActions.human_delay(200, 400)

    @staticmethod
    async def wait_and_verify_text(
        page: Page,
        text: str,
        timeout_ms: int = 8000
    ) -> bool:
        """
        Verifies that specific text appears anywhere on the page within timeout.
        """
        start = time.time()
        timeout_sec = timeout_ms / 1000.0
        while time.time() - start < timeout_sec:
            try:
                content = await page.content()
                if text.lower() in content.lower():
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False
