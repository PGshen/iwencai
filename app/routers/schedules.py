"""
Schedule management API router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.models.schemas import ScheduleCreate, ScheduleResponse
from app.models.db_models import Schedule, ScrapeConfig, PushConfig
from app.services.scheduler import scheduler_service
from app.database import get_db

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(db: AsyncSession = Depends(get_db)):
    """List all scheduled tasks."""
    result = await db.execute(select(Schedule))
    schedules = result.scalars().all()
    
    # Add next_run_time from scheduler
    response = []
    for schedule in schedules:
        job = scheduler_service.get_job(schedule.id)
        response.append(ScheduleResponse(
            id=schedule.id,
            name=schedule.name,
            cron_expression=schedule.cron_expression,
            scrape_config_id=schedule.scrape_config_id,
            push_config_id=schedule.push_config_id,
            enabled=schedule.enabled,
            next_run_time=job.next_run_time if job else None,
            created_at=schedule.created_at
        ))
    return response


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    schedule: ScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scheduled task."""
    # Verify scrape config exists
    result = await db.execute(
        select(ScrapeConfig).where(ScrapeConfig.id == schedule.scrape_config_id)
    )
    scrape_config = result.scalar_one_or_none()
    if not scrape_config:
        raise HTTPException(status_code=404, detail="Scrape config not found")
    
    # Verify push config if provided
    push_config = None
    if schedule.push_config_id:
        result = await db.execute(
            select(PushConfig).where(PushConfig.id == schedule.push_config_id)
        )
        push_config = result.scalar_one_or_none()
        if not push_config:
            raise HTTPException(status_code=404, detail="Push config not found")
    
    # Create database record
    db_schedule = Schedule(**schedule.model_dump())
    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)
    
    # Add to scheduler if enabled
    if schedule.enabled:
        scrape_config_dict = {
            "url": scrape_config.url,
            "method": scrape_config.method,
            "headers": scrape_config.headers,
            "params": scrape_config.params,
            "body": scrape_config.body,
            "parser_code": scrape_config.parser_code
        }
        push_config_dict = None
        if push_config:
            push_config_dict = {
                "channel": push_config.channel,
                "webhook_url": push_config.webhook_url
            }
        
        scheduler_service.add_job(
            db_schedule.id,
            schedule.cron_expression,
            scrape_config_dict,
            push_config_dict
        )
    
    job = scheduler_service.get_job(db_schedule.id)
    return ScheduleResponse(
        id=db_schedule.id,
        name=db_schedule.name,
        cron_expression=db_schedule.cron_expression,
        scrape_config_id=db_schedule.scrape_config_id,
        push_config_id=db_schedule.push_config_id,
        enabled=db_schedule.enabled,
        next_run_time=job.next_run_time if job else None,
        created_at=db_schedule.created_at
    )


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a scheduled task."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Remove from scheduler
    scheduler_service.remove_job(schedule_id)
    
    # Remove from database
    await db.delete(schedule)
    await db.commit()
    
    return {"message": "Schedule deleted successfully"}
