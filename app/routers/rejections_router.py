# app/routers/rejected_jobs_router.py
from __future__ import annotations
from fastapi import APIRouter, Depends, status
from app.core.auth import get_current_user
from app.utils.db_utils import get_db_cursor

from app.schemas.rejections import (
    PassJobIn,
    UndoJobIn,
    RejectedItem,
    RejectedListOut,
    StatusOut,
)

router = APIRouter(prefix="/rejected", tags=["rejected-jobs"])

SQL_INSERT_PASS = """
    INSERT INTO rejected_jobs (user_id, job_id, "timestamp")
    VALUES (%s, %s::uuid, NOW())
    ON CONFLICT (user_id, job_id) DO NOTHING
"""

SQL_DELETE_UNDO = """
    DELETE FROM rejected_jobs
    WHERE user_id = %s AND job_id = %s::uuid
"""

SQL_SELECT_LIST = """
    SELECT job_id, "timestamp"
    FROM rejected_jobs
    WHERE user_id = %s
    ORDER BY "timestamp" DESC
"""

SQL_SELECT_ONE = """
    SELECT 1
    FROM rejected_jobs
    WHERE user_id = %s AND job_id = %s::uuid
    LIMIT 1
"""

@router.post("/pass", status_code=status.HTTP_204_NO_CONTENT)
async def pass_job(
    payload: PassJobIn,
    user_id: str = Depends(get_current_user),
) -> None:
    # Accept both str and UUID in schema; cast to str for the driver
    job_id = str(payload.job_id)
    async with get_db_cursor() as cur:
        await cur.execute(SQL_INSERT_PASS, (user_id, job_id))
    return

@router.delete("/undo", status_code=status.HTTP_204_NO_CONTENT)
async def undo_pass(
    payload: UndoJobIn,
    user_id: str = Depends(get_current_user),
) -> None:
    job_id = str(payload.job_id)
    async with get_db_cursor() as cur:
        await cur.execute(SQL_DELETE_UNDO, (user_id, job_id))
    return

@router.get("", response_model=RejectedListOut)
async def list_rejected(
    user_id: str = Depends(get_current_user),
):
    async with get_db_cursor() as cur:
        await cur.execute(SQL_SELECT_LIST, (user_id,))
        rows = await cur.fetchall()  # rows are dicts (dict_row), per your pool config
    items = [RejectedItem(job_id=row["job_id"], timestamp=row["timestamp"]) for row in rows]
    return RejectedListOut(items=items, count=len(items))

@router.get("/{job_id}/status", response_model=StatusOut)
async def is_rejected(
    job_id: str,
    user_id: str = Depends(get_current_user),
):
    async with get_db_cursor() as cur:
        await cur.execute(SQL_SELECT_ONE, (user_id, str(job_id)))
        exists = await cur.fetchone()
    return StatusOut(job_id=job_id, is_rejected=exists is not None)
