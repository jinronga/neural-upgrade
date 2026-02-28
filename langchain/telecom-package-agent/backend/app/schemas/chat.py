from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    """Request body for sending a message to the agent."""

    user_id: Optional[int] = None
    message: str


class ChatMessageResponse(BaseModel):
    """Response from the agent."""

    reply: str

