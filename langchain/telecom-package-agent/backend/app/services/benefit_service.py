from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Benefit, User, UserBenefit


def get_pending_benefits(db: Session, user_id: int) -> list[Benefit]:
    user = db.get(User, user_id)
    if not user:
        return []

    claimed_subq = (
        select(UserBenefit.benefit_id).where(UserBenefit.user_id == user_id)
    )

    stmt = (
        select(Benefit)
        .where(Benefit.is_active.is_(True))
        .where(Benefit.id.not_in(claimed_subq))
    )
    return db.execute(stmt).scalars().all()


def claim_benefit(
    db: Session, user_id: int, benefit_id: int, channel: str | None = None
) -> UserBenefit | None:
    user = db.get(User, user_id)
    if not user:
        return None

    benefit = db.get(Benefit, benefit_id)
    if not benefit or not benefit.is_active or benefit.inventory <= 0:
        return None

    existing_stmt = select(UserBenefit).where(
        UserBenefit.user_id == user_id,
        UserBenefit.benefit_id == benefit_id,
    )
    existing = db.execute(existing_stmt).scalars().first()
    if existing:
        return None

    now = datetime.now(timezone.utc)
    user_benefit = UserBenefit(
        user_id=user_id,
        benefit_id=benefit_id,
        acquired_at=now,
        expires_at=None,
        status="active",
    )

    benefit.inventory -= 1

    db.add(user_benefit)
    db.commit()
    db.refresh(user_benefit)
    return user_benefit


def check_inventory(db: Session, benefit_id: int) -> int | None:
    benefit = db.get(Benefit, benefit_id)
    if not benefit:
        return None
    return benefit.inventory


def monthly_grant(db: Session) -> int:
    """Grant benefits to eligible users on a scheduled basis.

    Returns the number of user-benefit records created.
    """
    # This is a simplified placeholder strategy:
    #  - find all active benefits with inventory > 0
    #  - for each active user, grant one instance if not already owned
    from app.models import User  # imported here to avoid circular import

    active_benefits = db.execute(
        select(Benefit).where(Benefit.is_active.is_(True), Benefit.inventory > 0)
    ).scalars().all()

    if not active_benefits:
        return 0

    users = db.execute(
        select(User).where(User.status == "active")
    ).scalars().all()

    created_count = 0
    now = datetime.now(timezone.utc)

    for user in users:
        for benefit in active_benefits:
            if benefit.inventory <= 0:
                continue

            existing_stmt = select(UserBenefit).where(
                UserBenefit.user_id == user.id,
                UserBenefit.benefit_id == benefit.id,
            )
            exists = db.execute(existing_stmt).scalars().first()
            if exists:
                continue

            user_benefit = UserBenefit(
                user_id=user.id,
                benefit_id=benefit.id,
                acquired_at=now,
                expires_at=None,
                status="active",
            )
            benefit.inventory -= 1
            db.add(user_benefit)
            created_count += 1

    if created_count > 0:
        db.commit()

    return created_count

