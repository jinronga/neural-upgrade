from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PackageRead(BaseModel):
    """Package information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    monthly_fee: float
    data_quota_gb: float
    validity_days: int
    is_active: bool


class PackageRecommendRequest(BaseModel):
    """Request body for package recommendation."""

    monthly_budget: float | None = None
    min_data_gb: float | None = None
    limit: int = 3


class PackageRecommendResponse(BaseModel):
    """Recommended packages response."""

    recommendations: list[PackageRead]

