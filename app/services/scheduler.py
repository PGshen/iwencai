"""
Scheduler service for managing cron-based tasks.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
import logging

from app.models.schemas import ScrapeRequest, PushRequest, PushMessage
from app.services.scraper import scraper_service
from app.services.pusher.feishu import feishu_pusher
from app.services.pusher.discord import discord_pusher

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled scraping tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._started = False
    
    def start(self):
        """Start the scheduler."""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self._started:
            self.scheduler.shutdown()
            self._started = False
            logger.info("Scheduler shutdown")
    
    def add_job(
        self,
        job_id: str,
        cron_expression: str,
        scrape_config: dict,
        push_config: Optional[dict] = None
    ):
        """
        Add a scheduled job.
        
        Args:
            job_id: Unique job identifier
            cron_expression: Cron expression (e.g., "0 9 * * *" for 9 AM daily)
            scrape_config: Scrape configuration dict
            push_config: Optional push configuration dict
        """
        # Parse cron expression
        cron_parts = cron_expression.split()
        if len(cron_parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        trigger = CronTrigger(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            day_of_week=cron_parts[4]
        )
        
        self.scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            id=job_id,
            args=[scrape_config, push_config],
            replace_existing=True
        )
        logger.info(f"Added scheduled job: {job_id}")
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
    
    def get_job(self, job_id: str):
        """Get job information."""
        return self.scheduler.get_job(job_id)
    
    def get_jobs(self):
        """Get all jobs."""
        return self.scheduler.get_jobs()
    
    async def _execute_job(self, scrape_config: dict, push_config: Optional[dict]):
        """Execute a scheduled job."""
        try:
            # Execute scrape
            scrape_request = ScrapeRequest(**scrape_config)
            result = await scraper_service.scrape(scrape_request)
            
            if not result.success:
                logger.error(f"Scrape failed: {result.error}")
                return
            
            # Push result if configured
            if push_config:
                channel = push_config.get("channel", "feishu")
                webhook_url = push_config.get("webhook_url")
                
                message = PushMessage(
                    title="定时任务结果",
                    content=str(result.data),
                    type="text"
                )
                
                if channel == "feishu":
                    await feishu_pusher.push(webhook_url, message)
                elif channel == "discord":
                    await discord_pusher.push(webhook_url, message)
                
                logger.info("Scheduled job completed with push")
            else:
                logger.info("Scheduled job completed")
                
        except Exception as e:
            logger.error(f"Scheduled job failed: {e}")


# Singleton instance
scheduler_service = SchedulerService()
