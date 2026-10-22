import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..models import Task, Website, AuditLog, Recommendation, ChangeRecord
from ..core.config import settings

logger = logging.getLogger("ai_seo.automation.queue")

HIGH_RISK_OPERATIONS = {
    "delete_page",
    "modify_url_structure",
    "site_wide_canonical",
    "modify_robots_txt",
    "bulk_create_pages",
    "change_redirects",
    "modify_security_settings"
}

class TaskQueueManager:
    """
    Manages task execution, daily action limits, human approval gating,
    pausing, resuming, and retry policies.
    """

    def __init__(self):
        self.is_paused: bool = False
        self.stop_requested: bool = False
        self.daily_actions_count: int = 0
        self.current_task_id: Optional[str] = None

    def pause(self):
        self.is_paused = True
        logger.info("Automation engine PAUSED by user.")

    def resume(self):
        self.is_paused = False
        logger.info("Automation engine RESUMED.")

    def stop(self):
        self.stop_requested = True
        logger.info("Automation engine STOP requested.")

    def can_auto_execute(self, mode: str, task_type: str, risk_level: str) -> bool:
        """
        Determines whether a task requires human approval before proceeding.
        """
        if self.daily_actions_count >= settings.daily_action_limit:
            logger.warning("Daily action limit reached. Task requires explicit approval.")
            return False

        if task_type in HIGH_RISK_OPERATIONS or risk_level == "high":
            return False

        if mode == "recommendation":
            return False
        elif mode == "supervised":
            return False
        elif mode == "autonomous":
            return risk_level == "low"
        
        return False

    async def create_task(
        self,
        db: AsyncSession,
        website_id: int,
        task_type: str,
        payload: Dict[str, Any],
        risk_level: str = "low"
    ) -> Task:
        # Determine approval requirement based on website mode
        stmt = select(Website).where(Website.id == website_id)
        res = await db.execute(stmt)
        site = res.scalar_one_or_none()
        mode = site.automation_mode if site else "supervised"

        auto_ok = self.can_auto_execute(mode, task_type, risk_level)
        status = "pending" if auto_ok else "waiting_approval"
        requires_approval = not auto_ok

        task = Task(
            website_id=website_id,
            task_type=task_type,
            status=status,
            risk_level=risk_level,
            payload=payload,
            requires_human_approval=requires_approval
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        # Log audit
        audit = AuditLog(
            website_id=website_id,
            task_id=task.id,
            action=f"Task Queued: {task_type}",
            details={"risk_level": risk_level, "requires_approval": requires_approval, "mode": mode},
            status="pending"
        )
        db.add(audit)
        await db.commit()

        return task

    async def approve_task(self, db: AsyncSession, task_id: str) -> bool:
        """Approves a waiting task for execution."""
        stmt = select(Task).where(Task.id == task_id)
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            return False

        task.status = "pending"
        task.requires_human_approval = False
        await db.commit()
        return True

    async def reject_task(self, db: AsyncSession, task_id: str) -> bool:
        stmt = select(Task).where(Task.id == task_id)
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            return False

        task.status = "cancelled"
        await db.commit()
        return True

task_queue = TaskQueueManager()
