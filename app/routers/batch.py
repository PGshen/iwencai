"""
Batch run tasks API router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
import os
import asyncio
import logging

from app.models.schemas import BatchTaskCreate, BatchTaskResponse, BatchTaskItemResponse
from app.models.db_models import BatchTask, BusinessTemplate, BatchTaskItem
from app.database import get_db
from app.services.batch_runner import run_batch_task, stop_batch_task, RUNNING

router = APIRouter(prefix="/api/batch", tags=["batch"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[BatchTaskResponse])
async def list_batch_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BatchTask).order_by(BatchTask.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=BatchTaskResponse)
async def create_batch_task(task: BatchTaskCreate, db: AsyncSession = Depends(get_db)):
    # Validate template exists
    tpl_res = await db.execute(select(BusinessTemplate).where(BusinessTemplate.name == task.template_name))
    tpl = tpl_res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail=f"模板不存在: {task.template_name}")
    # Validate output dir and make sure writable
    out_dir = task.output_dir
    if not os.path.isabs(out_dir):
        if out_dir.startswith("data/"):
            out_dir = out_dir
        else:
            out_dir = os.path.join("data", out_dir)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"输出目录不可用: {e}")
    db_task = BatchTask(
        name=task.name,
        template_name=task.template_name,
        concurrency=str(task.concurrency),
        sleep_ms=str(task.sleep_ms),
        output_dir=out_dir,
        csv_text=task.csv_text,
        status="pending"
    )
    # Optional save fields and jsonpath
    try:
        db_task.save_fields = getattr(task, "save_fields", None)  # type: ignore
        db_task.data_json_path = getattr(task, "data_json_path", None)  # type: ignore
    except Exception:
        pass
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("/{task_id}", response_model=BatchTaskResponse)
async def get_batch_task(task_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BatchTask).where(BatchTask.id == task_id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.put("/{task_id}", response_model=BatchTaskResponse)
async def update_batch_task(task_id: str, update: BatchTaskCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BatchTask).where(BatchTask.id == task_id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    # Validate template
    tpl_res = await db.execute(select(BusinessTemplate).where(BusinessTemplate.name == update.template_name))
    if not tpl_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"模板不存在: {update.template_name}")
    # Validate output dir
    out_dir = update.output_dir
    if not os.path.isabs(out_dir):
        if out_dir.startswith("data/"):
            out_dir = out_dir
        else:
            out_dir = os.path.join("data", out_dir)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"输出目录不可用: {e}")
    task.name = update.name
    task.template_name = update.template_name
    task.concurrency = str(update.concurrency)
    task.sleep_ms = str(update.sleep_ms)
    task.output_dir = out_dir
    task.csv_text = update.csv_text
    task.status = "pending"
    try:
        task.save_fields = getattr(update, "save_fields", None)  # type: ignore
        task.data_json_path = getattr(update, "data_json_path", None)  # type: ignore
    except Exception:
        pass
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}")
async def delete_batch_task(task_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BatchTask).where(BatchTask.id == task_id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    await db.delete(task)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{task_id}/run")
async def run_batch(task_id: str, db: AsyncSession = Depends(get_db)):
    # Guard: prevent duplicate run using in-process control
    if RUNNING.get(task_id):
        return {"message": "任务已在执行中"}

    res = await db.execute(select(BatchTask).where(BatchTask.id == task_id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    tpl_res = await db.execute(select(BusinessTemplate).where(BusinessTemplate.name == task.template_name))
    tpl = tpl_res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail=f"模板不存在: {task.template_name}")
    # Update task status to running and mark previous items canceled
    await db.execute(update(BatchTask).where(BatchTask.id == task_id).values(status="running"))
    await db.execute(
        update(BatchTaskItem).where(BatchTaskItem.task_id == task_id).values(status="canceled")
    )
    await db.commit()

    async def _execute():
        logger.info(f"Batch task started: {task.id} name={task.name}")
        try:
            await run_batch_task(task, tpl)
            from app.database import async_session
            async with async_session() as s:
                await s.execute(update(BatchTask).where(BatchTask.id == task_id).values(status="completed"))
                await s.commit()
            logger.info(f"Batch task completed: {task.id}")
        except Exception as e:
            logger.exception(f"Batch task failed: {task.id} error={e}")
            from app.database import async_session
            async with async_session() as s:
                await s.execute(update(BatchTask).where(BatchTask.id == task_id).values(status="failed"))
                await s.commit()

    asyncio.create_task(_execute())
    return {"message": "任务已开始执行"}


@router.get("/{task_id}/items", response_model=List[BatchTaskItemResponse])
async def list_batch_items(task_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BatchTaskItem).where(BatchTaskItem.task_id == task_id).order_by(BatchTaskItem.seq_no))
    return res.scalars().all()


@router.post("/{task_id}/stop")
async def stop_batch(task_id: str):
    stopped = await stop_batch_task(task_id)
    if not stopped:
        raise HTTPException(status_code=400, detail="任务未在执行或停止失败")
    # Set task back to pending so it can be edited
    try:
        from app.database import async_session
        async with async_session() as s:
            await s.execute(update(BatchTask).where(BatchTask.id == task_id).values(status="pending"))
            await s.commit()
    except Exception:
        pass
    return {"message": "任务已停止"}
