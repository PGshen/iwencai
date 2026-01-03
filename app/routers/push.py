"""
Push API router.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.schemas import PushRequest, PushResponse, PushMessage
from app.models.db_models import PushConfig
from app.services.pusher.feishu import feishu_pusher
from app.services.pusher.discord import discord_pusher
from app.database import get_db

router = APIRouter(prefix="/api", tags=["push"])


@router.post("/push", response_model=PushResponse)
async def push_message(
    request: PushRequest,
    db: AsyncSession = Depends(get_db)
) -> PushResponse:
    """
    Push a message to IM channel (Feishu or Discord).
    
    You can either:
    1. Provide webhook_url directly
    2. Use a pre-configured config by providing config_id
    """
    webhook_url = request.webhook_url
    channel = request.channel
    
    # If config_name is provided, load by unique name
    if request.config_name and not request.config_id:
        result = await db.execute(
            select(PushConfig).where(PushConfig.name == request.config_name)
        )
        config = result.scalar_one_or_none()
        if not config:
            return PushResponse(
                success=False,
                error=f"Config not found by name: {request.config_name}"
            )
        webhook_url = webhook_url or config.webhook_url
        channel = channel or config.channel
    
    # If config_id is provided, load from database
    if request.config_id:
        result = await db.execute(
            select(PushConfig).where(PushConfig.id == request.config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            return PushResponse(
                success=False,
                error=f"Config not found: {request.config_id}"
            )
        
        webhook_url = webhook_url or config.webhook_url
        channel = channel or config.channel
    
    if not webhook_url:
        return PushResponse(
            success=False,
            error="webhook_url is required"
        )
        
    if not channel:
         return PushResponse(
            success=False,
            error="channel is required (either in request or config)"
        )
    
    # Normalize message
    msg_obj = request.message
    if isinstance(msg_obj, str):
        msg_obj = PushMessage(content=msg_obj)

    # Route to appropriate pusher
    if channel == "feishu":
        return await feishu_pusher.push(webhook_url, msg_obj)
    elif channel == "discord":
        return await discord_pusher.push(webhook_url, msg_obj)
    else:
        return PushResponse(
            success=False,
            error=f"Unsupported channel: {channel}"
        )
