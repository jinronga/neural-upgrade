from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Package, UsageRecord, UserPackage


def get_all_packages(db: Session) -> list[Package]:
    stmt = select(Package).where(Package.is_active.is_(True))
    return db.execute(stmt).scalars().all()


def get_package_detail(db: Session, package_id: int) -> Package | None:
    return db.get(Package, package_id)


def recommend_package(
    db: Session, user_id: int | None, usage_data: Mapping[str, float] | None = None
) -> list[Package]:
    """Simple recommendation based on historical or provided usage.

    usage_data can contain keys like:
      - "avg_monthly_used_gb"
      - "max_monthly_budget"
    """
    stmt = select(Package).where(Package.is_active.is_(True))

    avg_used_gb: float | None = None
    max_budget: float | None = None

    if usage_data is not None:
        avg_used_gb = usage_data.get("avg_monthly_used_gb")  # type: ignore[arg-type]
        max_budget = usage_data.get("max_monthly_budget")  # type: ignore[arg-type]

    if user_id is not None and avg_used_gb is None:
        # Derive a rough average GB usage from the last 30 days of usage records if needed.
        from sqlalchemy import func

        stmt_usage = (
            select(func.coalesce(func.sum(UsageRecord.used_mb), 0.0))
            .where(UsageRecord.user_id == user_id)
        )
        total_used_mb = db.execute(stmt_usage).scalar_one()
        if total_used_mb > 0:
            avg_used_gb = float(total_used_mb) / 1024.0

    if avg_used_gb is not None:
        stmt = stmt.where(Package.data_quota_gb >= avg_used_gb)

    if user_id is not None and max_budget is None:
        # Use current active packages' monthly fee as a soft budget reference.
        from sqlalchemy import func

        stmt_budget = (
            select(func.coalesce(func.sum(Package.monthly_fee), 0.0))
            .join(UserPackage, UserPackage.package_id == Package.id)
            .where(UserPackage.user_id == user_id, UserPackage.status == "active")
        )
        max_budget = db.execute(stmt_budget).scalar_one()

    if max_budget is not None:
        stmt = stmt.where(Package.monthly_fee <= max_budget)

    stmt = stmt.order_by(Package.monthly_fee.asc())
    return db.execute(stmt).scalars().all()


def calculate_upgrade_cost(
    db: Session, user_id: int, target_package_id: int
) -> float | None:
    """Calculate incremental monthly fee if the user upgrades to target package."""
    target = db.get(Package, target_package_id)
    if not target:
        return None

    from sqlalchemy import func

    stmt = (
        select(func.coalesce(func.sum(Package.monthly_fee), 0.0))
        .join(UserPackage, UserPackage.package_id == Package.id)
        .where(UserPackage.user_id == user_id, UserPackage.status == "active")
    )
    current_monthly = db.execute(stmt).scalar_one()
    diff = float(target.monthly_fee) - float(current_monthly)
    return max(diff, 0.0)

