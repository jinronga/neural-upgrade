from __future__ import annotations

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    """Request body for sending a message to the agent."""

    user_id: int | None = None
    message: str


class ChatMessageResponse(BaseModel):
    """Response from the agent."""

    reply: str

