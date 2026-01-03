"""
Base class for message pushers.
"""
from abc import ABC, abstractmethod
from typing import Any
from app.models.schemas import PushMessage, PushResponse


class BasePusher(ABC):
    """Abstract base class for message pushers."""
    
    @abstractmethod
    async def push(self, webhook_url: str, message: PushMessage) -> PushResponse:
        """
        Push a message to the target channel.
        
        Args:
            webhook_url: Webhook URL for the channel
            message: Message content to push
        
        Returns:
            PushResponse with success status
        """
        pass
