from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    phone_number: str = Field(min_length=5, max_length=20)
    name: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    status: str = Field(default="active", min_length=1, max_length=20)
    registered_at: Optional[datetime] = None


class UserCreate(UserBase):
    """Request body for creating user phone records."""


class UserUpdate(BaseModel):
    """Request body for updating user phone records."""

    phone_number: Optional[str] = Field(default=None, min_length=5, max_length=20)
    name: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, min_length=1, max_length=20)
    registered_at: Optional[datetime] = None


class UserRead(BaseModel):
    """User information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    status: str
    registered_at: Optional[datetime] = None


class UserPageResponse(BaseModel):
    """Paginated users response."""

    items: list[UserRead]
    page: int
    page_size: int
    total: int


class UserPackageAssignRequest(BaseModel):
    """Assign or switch package for a user."""

    package_id: int = Field(gt=0)
    effective_from: Optional[datetime] = None
    auto_renew: bool = False


class UserPackageRead(BaseModel):
    """User package relation with validity information."""

    id: int
    user_id: int
    phone_number: str
    package_id: int
    package_name: str
    monthly_fee: float
    data_quota_gb: float
    validity_days: int
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str
    auto_renew: bool
    is_current: bool


class UserPackagePageResponse(BaseModel):
    """Paginated user-package history response."""

    items: list[UserPackageRead]
    page: int
    page_size: int
    total: int


class UserCurrentPackageResponse(BaseModel):
    """Current valid package for one user."""

    item: Optional[UserPackageRead] = None
