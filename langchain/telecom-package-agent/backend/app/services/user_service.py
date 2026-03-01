from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Package, User, UserPackage
from app.services import user_package_service


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_packages(db: Session, user_id: int) -> list[Package]:
    stmt = (
        select(Package)
        .join(UserPackage, UserPackage.package_id == Package.id)
        .where(
            UserPackage.user_id == user_id,
            *user_package_service.active_user_package_filters(),
        )
        .order_by(UserPackage.start_date.desc(), UserPackage.id.desc())
    )
    return db.execute(stmt).scalars().all()


def get_user_value(db: Session, user_id: int) -> float:
    """Estimate user value based on active packages' monthly fee."""
    stmt = (
        select(func.coalesce(func.sum(Package.monthly_fee), 0.0))
        .join(UserPackage, UserPackage.package_id == Package.id)
        .where(
            UserPackage.user_id == user_id,
            *user_package_service.active_user_package_filters(),
        )
    )
    monthly_value = db.execute(stmt).scalar_one()
    # For now, approximate user value as 12 months of current monthly spending.
    return float(monthly_value) * 12.0
