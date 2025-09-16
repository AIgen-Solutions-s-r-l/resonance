# app/routers/rejected_jobs_router.py

from fastapi import APIRouter, Depends, status

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_async_session

from app.schemas.rejections import (
    PassJobIn,
    UndoJobIn,
    RejectedItem,
    RejectedListOut,
    StatusOut
)

router = APIRouter(prefix="/rejected", tags=["rejected-jobs"])


SQL_INSERT_PASS = text("""
    INSERT INTO rejected_jobs (user_id, job_id, "timestamp")
    VALUES (:user_id, :job_id, NOW())
    ON CONFLICT (user_id, job_id) DO NOTHING
""")

SQL_DELETE_UNDO = text("""
    DELETE FROM rejected_jobs
    WHERE user_id = :user_id AND job_id = :job_id
""")

SQL_SELECT_LIST = text("""
    SELECT job_id, "timestamp"
    FROM rejected_jobs
    WHERE user_id = :user_id
    ORDER BY "timestamp" DESC
""")

SQL_SELECT_ONE = text("""
    SELECT 1
    FROM rejected_jobs
    WHERE user_id = :user_id AND job_id = :job_id
    LIMIT 1
""")

@router.post("/pass", status_code=status.HTTP_204_NO_CONTENT)
async def pass_job(
    payload: PassJobIn,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Mark a job as 'passed' (rejected) for the current user.
    Idempotent: if (user_id, job_id) already exists, nothing happens.
    """
    await db.execute(SQL_INSERT_PASS, {"user_id": user_id, "job_id": payload.job_id})
    await db.commit()
    return


@router.delete("/undo", status_code=status.HTTP_204_NO_CONTENT)
async def undo_pass(
    payload: UndoJobIn,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Undo a previous 'pass' for this job (delete the (user_id, job_id) pair).
    No error if it didn't exist.
    """
    await db.execute(SQL_DELETE_UNDO, {"user_id": user_id, "job_id": payload.job_id})
    await db.commit()
    return


@router.get("", response_model=RejectedListOut)
async def list_rejected(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    List all rejected jobs for the current user.
    """
    res = await db.execute(SQL_SELECT_LIST, {"user_id": user_id})
    rows = res.fetchall()
    items = [RejectedItem(job_id=r[0], timestamp=r[1]) for r in rows]
    return RejectedListOut(items=items, count=len(items))


@router.get("/{job_id}/status", response_model=StatusOut)
async def is_rejected(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Check if a given job_id is currently rejected by the user.
    """
    res = await db.execute(SQL_SELECT_ONE, {"user_id": user_id, "job_id": job_id})
    exists = res.scalar() is not None
    return StatusOut(job_id=job_id, is_rejected=exists)
