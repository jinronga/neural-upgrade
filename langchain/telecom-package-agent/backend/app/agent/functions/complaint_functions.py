from __future__ import annotations

from app.database import SessionLocal
from app.models import Complaint, User


async def create_complaint(user_id: str, title: str, content: str) -> dict:
    """Create a complaint ticket for the user."""
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"success": False, "reason": "invalid_user_id"}

    try:
        user = db.get(User, user_id_int)
        if not user:
            return {"success": False, "reason": "user_not_found"}

        complaint = Complaint(
            user_id=user_id_int,
            title=title,
            content=content,
            status="open",
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        return {
            "success": True,
            "ticket_id": complaint.id,
            "status": complaint.status,
        }
    finally:
        db.close()

