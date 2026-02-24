from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    """User information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    name: str | None = None
    email: str | None = None
    status: str
    registered_at: datetime | None = None

