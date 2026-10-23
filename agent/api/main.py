import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..core.config import settings, SCREENSHOTS_DIR
from ..core.database import init_db, get_db
from ..core.security import get_current_token_auth
from ..models import Website, Task, CrawlResult, Recommendation
from ..browser.controller import browser_controller
from ..automation.scheduler import continuous_loop
from ..automation.queue import task_queue

from .routes import websites, gsc, crawler, keywords, cms, tasks, onboarding, pipeline, codebase, sitemap
from . import websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_seo.api.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SQLite database tables...")
    await init_db()
    logger.info(f"AI SEO Agent listening on http://{settings.host}:{settings.port}")
    logger.info(f"Dedicated Chrome profile: {settings.chrome_user_data_dir}")
    logger.info(f"Agent Pairing Token: {settings.agent_token}")
    
    # Start continuous loop scheduler
    continuous_loop.start()
    
    yield
    
    # Clean shutdown
    logger.info("Shutting down AI SEO Agent...")
    continuous_loop.stop()
    await browser_controller.stop()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Autonomous Browser-Controlled AI SEO Specialist Local Windows Agent",
    lifespan=lifespan
)

# Origin validation & CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://.*$|^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount screenshots directory
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

# Include Routers
app.include_router(websites.router)
app.include_router(gsc.router)
app.include_router(crawler.router)
app.include_router(keywords.router)
app.include_router(cms.router)
app.include_router(tasks.router)
app.include_router(onboarding.router)
app.include_router(pipeline.router)
app.include_router(codebase.router)
app.include_router(sitemap.router)
app.include_router(websocket.router)

@app.get("/api/status")
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """
    Public system status endpoint. Used by Chrome extension to verify connection.
    Returns agent readiness, pairing token requirement, and dedicated profile info.
    """
    site_count = (await db.execute(select(func.count(Website.id)))).scalar() or 0
    task_count = (await db.execute(select(func.count(Task.id)).where(Task.status.in_(["pending", "running"])))).scalar() or 0
    recs_count = (await db.execute(select(func.count(Recommendation.id)))).scalar() or 0

    return {
        "status": "online",
        "app_name": settings.app_name,
        "version": "1.0.0",
        "host": settings.host,
        "port": settings.port,
        "browser_running": browser_controller.is_running,
        "manual_takeover": browser_controller.manual_takeover_active,
        "chrome_profile": settings.chrome_user_data_dir,
        "gemini_configured": bool(settings.gemini_api_key),
        "engine_paused": task_queue.is_paused,
        "stats": {
            "websites": site_count,
            "active_tasks": task_count,
            "recommendations": recs_count,
            "daily_actions": task_queue.daily_actions_count,
            "daily_limit": settings.daily_action_limit
        }
    }
