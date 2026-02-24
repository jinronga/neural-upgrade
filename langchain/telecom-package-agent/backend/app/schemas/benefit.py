from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BenefitRead(BaseModel):
    """Benefit information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool
    inventory: int


class BenefitClaimRequest(BaseModel):
    """Request body for claiming a benefit."""

    user_id: int
    benefit_id: int


class BenefitClaimResponse(BaseModel):
    """Response after successfully claiming a benefit."""

    user_id: int
    benefit_id: int
    status: str


class BenefitInventoryResponse(BaseModel):
    """Inventory information for a benefit."""

    benefit_id: int
    inventory: int

