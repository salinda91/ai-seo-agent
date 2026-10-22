import os
import asyncio
import logging
import subprocess
import inspect
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
import httpx
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from ..core.config import settings, SCREENSHOTS_DIR
from .inspector import PageInspector
from .actions import BrowserActions
from .recovery import ObstacleDetector

logger = logging.getLogger("ai_seo.browser.controller")

class BrowserController:
    """
    Core Browser Interaction Engine using Playwright with a persistent, dedicated Chrome profile.
    Maintains session state (Google login, CMS cookies) in the isolated profile.
    Supports seamless CDP attachment (port 9222) and automatic stale-lock recovery.
    """

    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self._active_page: Optional[Page] = None
        self.is_running: bool = False
        self.manual_takeover_active: bool = False
        self.status_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.user_data_dir = Path(settings.chrome_user_data_dir)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]):
        """Subscribes a listener (e.g., WebSocket broadcaster) to browser events."""
        self.status_listeners.append(listener)

    async def _notify(self, event_type: str, data: Dict[str, Any]):
        payload = {
            "event": event_type,
            "data": data,
            "browser_running": self.is_running,
            "manual_takeover": self.manual_takeover_active
        }
        for listener in self.status_listeners:
            try:
                if inspect.iscoroutinefunction(listener):
                    await listener(payload)
                else:
                    listener(payload)
            except Exception as e:
                logger.debug(f"Error notifying listener: {e}")

    def _on_context_close(self):
        logger.info("Browser window was closed by user.")
        self.is_running = False
        self.context = None
        self._active_page = None
        asyncio.create_task(self._notify("browser_stopped", {}))

    def _on_page_open(self, page: Page):
        self._active_page = page

    async def _is_cdp_ready(self, port: int = 9222) -> bool:
        """Checks if Chrome is already active on localhost remote debugging port."""
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                r = await client.get(f"http://127.0.0.1:{port}/json/version")
                return r.status_code == 200
        except Exception:
            return False

    def _cleanup_stale_profile_locks(self):
        """
        Terminates only Chrome processes dedicated to AI_SEO_Agent that locked the profile,
        releasing SingletonLock files without affecting any personal Chrome instances.
        """
        try:
            ps_cmd = (
                "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | "
                "Where-Object { $_.CommandLine -like '*AI_SEO_Agent*' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                timeout=6,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.debug(f"Lock cleanup notice: {e}")

        # Remove stale lock files in dedicated profile
        for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            lock_path = self.user_data_dir / lock_name
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except Exception:
                pass

    async def start(self, headless: bool = False) -> bool:
        """
        Launches or attaches to the dedicated Chrome browser session.
        Uses CDP connection (port 9222) if available, or launches persistent context with auto-recovery.
        """
        async with self._lock:
            if self.is_running and self.context:
                return True

            try:
                if not self.playwright:
                    self.playwright = await async_playwright().start()

                # Strategy 1: Attach to existing Chrome session via Chrome DevTools Protocol
                if await self._is_cdp_ready(9222):
                    try:
                        logger.info("Found active Chrome on remote-debugging-port 9222. Connecting via CDP...")
                        browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
                        if browser.contexts:
                            self.context = browser.contexts[0]
                        else:
                            self.context = await browser.new_context()

                        self.context.on("close", lambda: self._on_context_close())
                        self.context.on("page", lambda p: self._on_page_open(p))

                        pages = self.context.pages
                        if pages:
                            self._active_page = pages[0]
                        else:
                            self._active_page = await self.context.new_page()

                        self.is_running = True
                        logger.info("Successfully connected to existing Chrome session via CDP!")
                        await self._notify("browser_started", {"cdp": True, "port": 9222})
                        return True
                    except Exception as e:
                        logger.warning(f"CDP connection attempt failed, falling back to persistent launch: {e}")

                # Strategy 2: Launch dedicated Chrome profile with --remote-debugging-port=9222
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--remote-debugging-port=9222",
                    "--window-size=1366,768",
                ]

                executable_path = settings.chrome_executable if os.path.exists(settings.chrome_executable) else None

                for attempt in range(2):
                    try:
                        self.context = await self.playwright.chromium.launch_persistent_context(
                            user_data_dir=str(self.user_data_dir),
                            executable_path=executable_path,
                            headless=headless,
                            viewport={"width": 1366, "height": 768},
                            args=launch_args,
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
                        )

                        self.context.on("close", lambda: self._on_context_close())
                        self.context.on("page", lambda p: self._on_page_open(p))

                        pages = self.context.pages
                        if pages:
                            self._active_page = pages[0]
                        else:
                            self._active_page = await self.context.new_page()

                        self.is_running = True
                        logger.info(f"Browser controller started with dedicated profile at: {self.user_data_dir}")
                        await self._notify("browser_started", {"profile": str(self.user_data_dir), "headless": headless})
                        return True
                    except Exception as e:
                        err_str = str(e)
                        if "Opening in existing browser session" in err_str or "already in use" in err_str:
                            logger.warning("Detected stale Chrome process locking the profile. Recovering...")
                            self._cleanup_stale_profile_locks()
                            await asyncio.sleep(1.0)
                            continue
                        else:
                            logger.error(f"Failed to start browser controller: {e}")
                            break

                self.is_running = False
                self.context = None
                return False

            except Exception as e:
                logger.error(f"Fatal error starting browser controller: {e}")
                self.is_running = False
                self.context = None
                return False

    async def stop(self):
        """Closes browser context and Playwright instance."""
        async with self._lock:
            try:
                if self.context:
                    await self.context.close()
                if self.playwright:
                    await self.playwright.stop()
            except Exception as e:
                logger.debug(f"Error during browser stop: {e}")
            finally:
                self.context = None
                self.playwright = None
                self._active_page = None
                self.is_running = False
                logger.info("Browser controller stopped.")
                await self._notify("browser_stopped", {})

    def get_current_page(self) -> Optional[Page]:
        """
        Passive getter: returns active page IF browser is already open and running.
        NEVER starts the browser and NEVER creates a new tab.
        """
        if not self.is_running or not self.context:
            return None
        
        try:
            if self._active_page and not self._active_page.is_closed():
                return self._active_page

            pages = self.context.pages
            for p in pages:
                if not p.is_closed():
                    self._active_page = p
                    return self._active_page
        except Exception:
            self.is_running = False
            self.context = None
            self._active_page = None

        return None

    async def get_page(self) -> Page:
        """
        Active getter: ensures an active page is ready when an action must execute.
        Reuses existing open tab whenever possible.
        """
        current = self.get_current_page()
        if current:
            return current

        # Need to start or reopen
        if not self.is_running or not self.context:
            started = await self.start()
            if not started:
                raise RuntimeError("Failed to launch dedicated Chrome browser session.")

        # Re-check after start
        try:
            pages = self.context.pages if self.context else []
            for p in pages:
                if not p.is_closed():
                    self._active_page = p
                    return self._active_page

            # Only create a tab if zero open tabs exist in the window
            if self.context:
                self._active_page = await self.context.new_page()
                return self._active_page
        except Exception as e:
            logger.warning(f"Error getting page, resetting browser: {e}")
            await self.stop()
            await self.start()
            if self.context and self.context.pages:
                self._active_page = self.context.pages[0]
                return self._active_page
            elif self.context:
                self._active_page = await self.context.new_page()
                return self._active_page

        raise RuntimeError("Unable to obtain a browser page.")

    async def navigate(self, url: str, wait_until: str = "load", timeout_ms: int = 30000) -> Dict[str, Any]:
        """
        Navigates to a URL, captures before/after state, and checks for obstacles (CAPTCHA, MFA).
        """
        page = await self.get_page()
        try:
            logger.info(f"Navigating to {url}")
            response = await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            await BrowserActions.human_delay(400, 800)

            # Check for blocking obstacles
            has_obstacle, obstacle_type, details = await ObstacleDetector.check_obstacles(page)
            screenshot_path = await BrowserActions.capture_screenshot(page, "navigated")

            status_code = response.status if response else 200
            result = {
                "success": not has_obstacle,
                "url": page.url,
                "title": await page.title(),
                "status_code": status_code,
                "screenshot": screenshot_path,
                "has_obstacle": has_obstacle,
                "obstacle_type": obstacle_type,
                "details": details
            }

            if has_obstacle:
                logger.warning(f"Obstacle detected ({obstacle_type}): {details}")
                self.manual_takeover_active = True
                await self._notify("obstacle_detected", result)
            else:
                await self._notify("navigated", result)

            return result
        except Exception as e:
            logger.error(f"Navigation to {url} failed: {e}")
            screenshot_path = ""
            try:
                screenshot_path = await BrowserActions.capture_screenshot(page, "nav_error")
            except Exception:
                pass
            return {
                "success": False,
                "url": url,
                "title": "",
                "status_code": 0,
                "screenshot": screenshot_path,
                "has_obstacle": False,
                "obstacle_type": "error",
                "details": str(e)
            }

    async def inspect(self) -> Dict[str, Any]:
        """Returns comprehensive page summary and interactive element catalog."""
        page = await self.get_page()
        summary = await PageInspector.get_page_summary(page)
        interactive = await PageInspector.extract_interactive_elements(page)
        screenshot = await BrowserActions.capture_screenshot(page, "inspect")
        
        data = {
            **summary,
            "interactive_elements": interactive,
            "screenshot": screenshot
        }
        await self._notify("page_inspected", {"url": summary.get("url", ""), "elements_count": len(interactive)})
        return data

    async def click_element(self, selector_or_locator: Any) -> Tuple[bool, str, Dict[str, str]]:
        page = await self.get_page()
        result = await BrowserActions.human_click(page, selector_or_locator)
        await self._notify("action_clicked", {"result": result[0], "message": result[1]})
        return result

    async def fill_field(self, selector_or_locator: Any, text: str) -> bool:
        page = await self.get_page()
        success = await BrowserActions.human_type(page, selector_or_locator, text)
        await self._notify("action_typed", {"success": success, "length": len(text)})
        return success

    async def capture_live_frame(self) -> str:
        """Captures a quick screenshot for live browser stream without force-launching."""
        current = self.get_current_page()
        if not current:
            return ""
        try:
            return await BrowserActions.capture_screenshot(current, "live_frame")
        except Exception:
            return ""

    def set_takeover(self, active: bool):
        """Enables or disables manual human takeover mode."""
        self.manual_takeover_active = active
        logger.info(f"Manual takeover mode set to: {active}")

# Global singleton browser controller
browser_controller = BrowserController()
