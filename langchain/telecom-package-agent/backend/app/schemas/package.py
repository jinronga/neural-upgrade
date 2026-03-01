from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PackageRead(BaseModel):
    """Package information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    monthly_fee: float
    data_quota_gb: float
    validity_days: int
    is_active: bool


class PackageBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    monthly_fee: float = Field(ge=0)
    data_quota_gb: float = Field(ge=0)
    validity_days: int = Field(default=30, ge=1)
    is_active: bool = True


class PackageCreate(PackageBase):
    """Request body for creating a package."""


class PackageUpdate(BaseModel):
    """Request body for updating a package."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    monthly_fee: Optional[float] = Field(default=None, ge=0)
    data_quota_gb: Optional[float] = Field(default=None, ge=0)
    validity_days: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class PackageRecommendRequest(BaseModel):
    """Request body for package recommendation."""

    monthly_budget: Optional[float] = None
    min_data_gb: Optional[float] = None
    limit: int = 3


class PackageRecommendResponse(BaseModel):
    """Recommended packages response."""

    recommendations: List[PackageRead]


class PackagePageResponse(BaseModel):
    """Paginated packages response."""

    items: List[PackageRead]
    page: int
    page_size: int
    total: int
