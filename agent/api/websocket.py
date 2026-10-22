import asyncio
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..core.security import verify_token
from ..browser.controller import browser_controller
from ..browser.actions import BrowserActions

logger = logging.getLogger("ai_seo.api.websocket")

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        dead = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.add(conn)
        for d in dead:
            self.active_connections.discard(d)

manager = ConnectionManager()

# Hook browser controller notifications into WebSocket broadcast
async def browser_event_listener(event_dict: dict):
    await manager.broadcast(event_dict)

browser_controller.subscribe(browser_event_listener)

@router.websocket("/ws/browser-feed")
async def websocket_browser_feed(websocket: WebSocket, token: str = Query(None)):
    if not verify_token(token):
        await websocket.close(code=4001, reason="Unauthorized: invalid pairing token")
        return

    await manager.connect(websocket)
    try:
        # Send initial status WITHOUT launching browser or opening tabs!
        current_page = browser_controller.get_current_page()
        initial_url = ""
        initial_title = ""
        if current_page:
            try:
                initial_url = current_page.url
                initial_title = await current_page.title()
            except Exception:
                pass

        await websocket.send_json({
            "event": "connected",
            "url": initial_url,
            "title": initial_title,
            "browser_running": browser_controller.is_running,
            "manual_takeover": browser_controller.manual_takeover_active
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                cmd = msg.get("command")
                
                if cmd == "takeover_toggle":
                    enable = msg.get("enable", False)
                    browser_controller.set_takeover(enable)
                    await manager.broadcast({
                        "event": "takeover_status",
                        "active": browser_controller.manual_takeover_active
                    })

                elif cmd == "navigate":
                    target_url = msg.get("url")
                    if target_url:
                        asyncio.create_task(browser_controller.navigate(target_url))

                elif cmd == "capture_frame":
                    current_page = browser_controller.get_current_page()
                    if current_page:
                        try:
                            shot = await browser_controller.capture_live_frame()
                            await websocket.send_json({
                                "event": "live_frame",
                                "screenshot": shot,
                                "url": current_page.url,
                                "title": await current_page.title()
                            })
                        except Exception:
                            pass

                elif cmd == "click_coordinates":
                    current_page = browser_controller.get_current_page()
                    if current_page:
                        x = msg.get("x")
                        y = msg.get("y")
                        if x is not None and y is not None:
                            try:
                                await current_page.mouse.click(x, y)
                                await BrowserActions.human_delay(200, 400)
                                shot = await browser_controller.capture_live_frame()
                                await websocket.send_json({
                                    "event": "live_frame",
                                    "screenshot": shot,
                                    "url": current_page.url
                                })
                            except Exception:
                                pass

                elif cmd == "type_text":
                    current_page = browser_controller.get_current_page()
                    if current_page:
                        text = msg.get("text", "")
                        try:
                            await current_page.keyboard.type(text)
                        except Exception:
                            pass

            except Exception as e:
                logger.warning(f"Error handling websocket message: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection exception: {e}")
        manager.disconnect(websocket)
