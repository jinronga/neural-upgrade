from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import User


def query_realtime_balance(db: Session, user_id: int) -> float | None:
    """Query user's realtime balance.

    In a real system this would call an external billing platform.
    For now, return a synthetic balance based on user id.
    """
    user = db.get(User, user_id)
    if not user:
        return None

    # Simple placeholder: make balance depend on user id to avoid a fixed constant.
    base = 100.0
    return base - (user_id % 10)


def process_refund(
    db: Session, user_id: int, amount: float, reason: str
) -> dict[str, Any] | None:
    """Process a refund request.

    In a real system this would:
      - call billing system API,
      - persist a refund record,
      - handle idempotency and error cases.
    Here we return a simple result dict to indicate success.
    """
    if amount <= 0:
        return None

    user = db.get(User, user_id)
    if not user:
        return None

    # Placeholder "success" response
    return {
        "user_id": user_id,
        "amount": float(amount),
        "reason": reason,
        "status": "success",
    }

