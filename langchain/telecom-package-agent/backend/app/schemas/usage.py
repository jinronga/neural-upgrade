from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UsageCurrentResponse(BaseModel):
    """Current usage summary for a user."""

    user_id: int
    total_used_mb: float


class UsageRecordItem(BaseModel):
    """Single usage record entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    record_time: datetime
    used_mb: float
    network_type: str | None = None
    location: str | None = None

