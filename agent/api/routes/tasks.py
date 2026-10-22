from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ...core.database import get_db
from ...core.security import get_current_token_auth
from ...models import Task, AuditLog
from ...automation.queue import task_queue

router = APIRouter(prefix="/api/tasks", tags=["Task Queue & Controls"], dependencies=[Depends(get_current_token_auth)])

class ControlRequest(BaseModel):
    action: str  # "pause", "resume", "stop"

@router.get("")
async def list_tasks(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).order_by(Task.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    tasks = res.scalars().all()
    return [
        {
            "id": t.id,
            "website_id": t.website_id,
            "task_type": t.task_type,
            "status": t.status,
            "risk_level": t.risk_level,
            "payload": t.payload,
            "result": t.result,
            "error_message": t.error_message,
            "requires_human_approval": t.requires_human_approval,
            "created_at": t.created_at
        }
        for t in tasks
    ]

@router.post("/control")
async def control_engine(payload: ControlRequest):
    act = payload.action.lower()
    if act == "pause":
        task_queue.pause()
    elif act == "resume":
        task_queue.resume()
    elif act == "stop":
        task_queue.stop()
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'pause', 'resume', or 'stop'.")
    
    return {
        "success": True,
        "is_paused": task_queue.is_paused,
        "stop_requested": task_queue.stop_requested
    }

@router.post("/{task_id}/approve")
async def approve_task(task_id: str, db: AsyncSession = Depends(get_db)):
    ok = await task_queue.approve_task(db, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"success": True, "message": f"Task {task_id} approved for execution."}

@router.post("/{task_id}/reject")
async def reject_task(task_id: str, db: AsyncSession = Depends(get_db)):
    ok = await task_queue.reject_task(db, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"success": True, "message": f"Task {task_id} rejected and cancelled."}

@router.get("/audit-logs")
async def list_audit_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [
        {
            "id": l.id,
            "website_id": l.website_id,
            "task_id": l.task_id,
            "action": l.action,
            "details": l.details,
            "status": l.status,
            "created_at": l.created_at
        }
        for l in logs
    ]
