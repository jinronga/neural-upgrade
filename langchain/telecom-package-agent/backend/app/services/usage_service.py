from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import UsageRecord, User

try:  # optional Redis support
    from redis import Redis
except Exception:  # pragma: no cover - type fallback
    Redis = Any  # type: ignore[misc, assignment]


def _cache_key_current_usage(user_id: int) -> str:
    return f"user:{user_id}:current_usage_mb"


def get_current_usage(
    db: Session,
    user_id: int,
    redis_client: Redis | None = None,
    ttl_seconds: int = 60,
) -> float:
    user = db.get(User, user_id)
    if not user:
        return 0.0

    if redis_client is not None:
        key = _cache_key_current_usage(user_id)
        cached = redis_client.get(key)
        if cached is not None:
            try:
                return float(cached)
            except (TypeError, ValueError):
                pass

    stmt = select(func.coalesce(func.sum(UsageRecord.used_mb), 0.0)).where(
        UsageRecord.user_id == user_id
    )
    total_used_mb = float(db.execute(stmt).scalar_one())

    if redis_client is not None:
        key = _cache_key_current_usage(user_id)
        redis_client.setex(key, ttl_seconds, str(total_used_mb))

    return total_used_mb


def get_usage_history(
    db: Session, user_id: int, months: int = 6
) -> list[UsageRecord]:
    user = db.get(User, user_id)
    if not user:
        return []

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30 * months)

    stmt = (
        select(UsageRecord)
        .where(UsageRecord.user_id == user_id, UsageRecord.record_time >= since)
        .order_by(UsageRecord.record_time.desc())
    )
    return db.execute(stmt).scalars().all()


def check_threshold(
    db: Session, user_id: int, threshold_mb: float = 0.0
) -> bool:
    """Return True if user usage exceeds the given threshold."""
    if threshold_mb <= 0:
        return False

    current_usage = get_current_usage(db, user_id, redis_client=None)
    return current_usage >= threshold_mb


