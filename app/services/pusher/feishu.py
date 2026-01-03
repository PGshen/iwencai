"""
Feishu (飞书) message pusher using webhook.
"""
import httpx
from app.models.schemas import PushMessage, PushResponse
from app.services.pusher.base import BasePusher


class FeishuPusher(BasePusher):
    """Feishu webhook message pusher."""
    
    async def push(self, webhook_url: str, message: PushMessage) -> PushResponse:
        """
        Push a message to Feishu via webhook.
        
        Feishu webhook API documentation:
        https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
        """
        try:
            payload = self._build_payload(message)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                # Feishu returns code 0 on success
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    return PushResponse(
                        success=True,
                        message="Message sent to Feishu successfully"
                    )
                else:
                    return PushResponse(
                        success=False,
                        error=f"Feishu API error: {result.get('msg', 'Unknown error')}"
                    )
                    
        except httpx.HTTPStatusError as e:
            return PushResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            return PushResponse(
                success=False,
                error=f"Failed to push to Feishu: {str(e)}"
            )
    
    def _build_payload(self, message: PushMessage) -> dict:
        """Build Feishu webhook payload based on message type."""
        
        if message.type == "text":
            return {
                "msg_type": "text",
                "content": {
                    "text": self._format_text_content(message)
                }
            }
        
        elif message.type == "markdown":
            # Feishu uses "interactive" card for rich content
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": message.title or "通知"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": message.content
                        }
                    ]
                }
            }
        
        elif message.type == "card":
            # Full card format
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": message.title or "通知"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": message.content
                            }
                        }
                    ]
                }
            }
        
        # Default to text
        return {
            "msg_type": "text",
            "content": {
                "text": self._format_text_content(message)
            }
        }
    
    def _format_text_content(self, message: PushMessage) -> str:
        """Format text content with optional title."""
        if message.title:
            return f"【{message.title}】\n{message.content}"
        return message.content


# Singleton instance
feishu_pusher = FeishuPusher()
