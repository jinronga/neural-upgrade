from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    """User information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    status: str
    registered_at: Optional[datetime] = None

