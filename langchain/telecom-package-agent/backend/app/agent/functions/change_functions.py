from __future__ import annotations

from app.database import SessionLocal
from app.services import package_service


async def estimate_upgrade_cost(user_id: str, target_package_id: str) -> dict:
    """Estimate the incremental monthly fee to upgrade to a target package."""
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
        target_id_int = int(target_package_id)
    except ValueError:
        return {"success": False, "reason": "invalid_id"}

    try:
        diff = package_service.calculate_upgrade_cost(db, user_id_int, target_id_int)
        if diff is None:
            return {"success": False, "reason": "package_not_found"}
        return {"success": True, "upgrade_cost": diff}
    finally:
        db.close()

