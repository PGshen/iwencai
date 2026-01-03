"""
Discord message pusher using webhook.
"""
import httpx
from app.models.schemas import PushMessage, PushResponse
from app.services.pusher.base import BasePusher


class DiscordPusher(BasePusher):
    """Discord webhook message pusher."""
    
    async def push(self, webhook_url: str, message: PushMessage) -> PushResponse:
        """
        Push a message to Discord via webhook.
        
        Discord webhook API documentation:
        https://discord.com/developers/docs/resources/webhook#execute-webhook
        """
        try:
            payload = self._build_payload(message)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)
                
                # Discord returns 204 No Content on success
                if response.status_code in [200, 204]:
                    return PushResponse(
                        success=True,
                        message="Message sent to Discord successfully"
                    )
                else:
                    return PushResponse(
                        success=False,
                        error=f"Discord API error: {response.status_code} - {response.text}"
                    )
                    
        except httpx.HTTPStatusError as e:
            return PushResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            return PushResponse(
                success=False,
                error=f"Failed to push to Discord: {str(e)}"
            )
    
    def _build_payload(self, message: PushMessage) -> dict:
        """Build Discord webhook payload based on message type."""
        
        if message.type == "text":
            content = message.content
            if message.title:
                content = f"**{message.title}**\n{message.content}"
            return {"content": content}
        
        elif message.type in ["markdown", "card"]:
            # Use Discord embed for rich content
            embed = {
                "description": message.content,
                "color": 3447003  # Blue color
            }
            if message.title:
                embed["title"] = message.title
            
            return {"embeds": [embed]}
        
        # Default to plain text
        return {"content": message.content}


# Singleton instance
discord_pusher = DiscordPusher()
