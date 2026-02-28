from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


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


class PackageRecommendRequest(BaseModel):
    """Request body for package recommendation."""

    monthly_budget: Optional[float] = None
    min_data_gb: Optional[float] = None
    limit: int = 3


class PackageRecommendResponse(BaseModel):
    """Recommended packages response."""

    recommendations: List[PackageRead]

