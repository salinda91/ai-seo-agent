import pytest
import pytest_asyncio
from agent.browser.controller import browser_controller

@pytest.mark.asyncio
async def test_browser_passive_getter():
    # Calling get_current_page() when idle must NOT start the browser
    assert not browser_controller.is_running
    page = browser_controller.get_current_page()
    assert page is None
    assert not browser_controller.is_running

@pytest.mark.asyncio
async def test_browser_start_and_stop():
    # Calling start(headless=True) should launch and allow clean stop
    try:
        started = await browser_controller.start(headless=True)
        if started:
            assert browser_controller.is_running
            page = browser_controller.get_current_page()
            assert page is not None
            await browser_controller.stop()
            assert not browser_controller.is_running
            assert browser_controller.get_current_page() is None
    finally:
        await browser_controller.stop()
