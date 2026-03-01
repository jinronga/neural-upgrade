from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Package, User, UserPackage


def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.utcnow()


def active_user_package_filters(at: datetime | None = None):
    point = at or utc_now()
    return (
        UserPackage.status == "active",
        UserPackage.start_date <= point,
        or_(UserPackage.end_date.is_(None), UserPackage.end_date > point),
    )


def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def is_current_user_package(
    user_package: UserPackage, at: datetime | None = None
) -> bool:
    point = _to_utc_naive(at or utc_now())
    start = _to_utc_naive(user_package.start_date)
    end = _to_utc_naive(user_package.end_date) if user_package.end_date else None
    return (
        user_package.status == "active"
        and start <= point
        and (end is None or end > point)
    )


def get_current_user_package(
    db: Session,
    user_id: int,
    at: datetime | None = None,
) -> UserPackage | None:
    stmt = (
        select(UserPackage)
        .where(UserPackage.user_id == user_id, *active_user_package_filters(at))
        .order_by(UserPackage.start_date.desc(), UserPackage.id.desc())
    )
    return db.execute(stmt).scalars().first()


def list_user_packages_history(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[UserPackage], int]:
    total = db.scalar(
        select(func.count(UserPackage.id)).where(UserPackage.user_id == user_id)
    ) or 0

    stmt = (
        select(UserPackage)
        .where(UserPackage.user_id == user_id)
        .order_by(UserPackage.start_date.desc(), UserPackage.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(stmt).scalars().all()
    return items, int(total)


def assign_package_to_user(
    db: Session,
    user: User,
    package: Package,
    effective_from: datetime | None = None,
    auto_renew: bool = False,
) -> UserPackage:
    now = _to_utc_naive(effective_from or utc_now())

    active_rows = db.execute(
        select(UserPackage).where(
            UserPackage.user_id == user.id,
            UserPackage.status == "active",
        )
    ).scalars().all()

    for row in active_rows:
        row.status = "inactive"
        row.auto_renew = False
        row_start = _to_utc_naive(row.start_date)
        row_end = _to_utc_naive(row.end_date) if row.end_date else None
        if row_start >= now:
            row.end_date = row.start_date
        elif row_end is None or row_end > now:
            row.end_date = now

    validity_days = max(int(package.validity_days), 1)
    assigned = UserPackage(
        user_id=user.id,
        package_id=package.id,
        start_date=now,
        end_date=now + timedelta(days=validity_days),
        status="active",
        auto_renew=auto_renew,
    )
    db.add(assigned)
    db.flush()
    return assigned
