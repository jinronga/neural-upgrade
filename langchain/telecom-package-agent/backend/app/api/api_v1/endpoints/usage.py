from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.api_v1.dependencies import DBSessionDep
from app.models import UsageRecord, User
from app.schemas.usage import UsageCurrentResponse, UsageRecordItem

router = APIRouter()


@router.get("/current/{user_id}", response_model=UsageCurrentResponse)
def get_current_usage(user_id: int, db: DBSessionDep) -> UsageCurrentResponse:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt = select(func.coalesce(func.sum(UsageRecord.used_mb), 0.0)).where(
        UsageRecord.user_id == user_id
    )
    total_used_mb = db.execute(stmt).scalar_one()

    return UsageCurrentResponse(user_id=user_id, total_used_mb=total_used_mb)


@router.get("/history/{user_id}", response_model=list[UsageRecordItem])
def get_usage_history(user_id: int, db: DBSessionDep) -> list[UsageRecord]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt = (
        select(UsageRecord)
        .where(UsageRecord.user_id == user_id)
        .order_by(UsageRecord.record_time.desc())
    )
    result = db.execute(stmt).scalars().all()
    return result

