from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.api_v1.dependencies import DBSessionDep
from app.models import Benefit, User, UserBenefit
from app.schemas.benefit import (
    BenefitClaimRequest,
    BenefitClaimResponse,
    BenefitInventoryResponse,
    BenefitRead,
)

router = APIRouter()


@router.get("/pending/{user_id}", response_model=list[BenefitRead])
def get_pending_benefits(user_id: int, db: DBSessionDep) -> list[Benefit]:
    """Return benefits that the user can still claim."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Benefits that are active and not yet claimed by the user
    claimed_subq = (
        select(UserBenefit.benefit_id).where(UserBenefit.user_id == user_id)
    )

    stmt = (
        select(Benefit)
        .where(Benefit.is_active.is_(True))
        .where(Benefit.id.not_in(claimed_subq))
    )
    result = db.execute(stmt).scalars().all()
    return result


@router.post("/claim", response_model=BenefitClaimResponse)
def claim_benefit(payload: BenefitClaimRequest, db: DBSessionDep) -> BenefitClaimResponse:
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    benefit = db.get(Benefit, payload.benefit_id)
    if not benefit or not benefit.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Benefit not available"
        )

    if benefit.inventory <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Benefit out of stock"
        )

    existing_stmt = select(UserBenefit).where(
        UserBenefit.user_id == payload.user_id,
        UserBenefit.benefit_id == payload.benefit_id,
    )
    existing = db.execute(existing_stmt).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benefit already claimed by user",
        )

    now = datetime.now(timezone.utc)
    user_benefit = UserBenefit(
        user_id=payload.user_id,
        benefit_id=payload.benefit_id,
        acquired_at=now,
        expires_at=None,
        status="active",
    )

    benefit.inventory -= 1

    db.add(user_benefit)
    db.commit()

    return BenefitClaimResponse(
        user_id=payload.user_id,
        benefit_id=payload.benefit_id,
        status=user_benefit.status,
    )


@router.get("/inventory/{benefit_id}", response_model=BenefitInventoryResponse)
def get_benefit_inventory(benefit_id: int, db: DBSessionDep) -> BenefitInventoryResponse:
    benefit = db.get(Benefit, benefit_id)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Benefit not found"
        )

    return BenefitInventoryResponse(benefit_id=benefit.id, inventory=benefit.inventory)

