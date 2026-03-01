from __future__ import annotations

from typing import List

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Package, UsageRecord, UserPackage
from app.services import package_service, user_package_service


def _package_to_dict(pkg: Package) -> dict:
    return {
        "package_id": pkg.id,
        "name": pkg.name,
        "price": float(pkg.monthly_fee),
        "data_gb": float(pkg.data_quota_gb),
        "voice_minutes": None,
        "sms_count": None,
        "benefits": [],
        "status": "active" if pkg.is_active else "inactive",
    }


async def get_current_package(user_id: str) -> dict:
    """
    查询用户当前使用的套餐。

    返回一个包含套餐主信息和生效时间的字典。
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {}

    try:
        user_pkg = user_package_service.get_current_user_package(db, user_id_int)
        if not user_pkg or not user_pkg.package:
            return {}

        pkg = user_pkg.package
        data = _package_to_dict(pkg)
        data.update(
            {
                "start_date": user_pkg.start_date.date().isoformat(),
                "end_date": user_pkg.end_date.date().isoformat()
                if user_pkg.end_date
                else None,
                "status": user_pkg.status,
            }
        )
        return data
    finally:
        db.close()


async def get_available_packages(
    user_id: str | None = None, target_group: str | None = None
) -> List[dict]:
    """
    获取所有可用套餐。

    如果提供 user_id，会根据用户的当前支出水平将更接近的套餐排在前面。
    target_group 目前作为占位字段，方便后续扩展。
    """
    db = SessionLocal()
    try:
        packages = package_service.get_all_packages(db)

        if user_id is not None:
            try:
                user_id_int = int(user_id)
            except ValueError:
                user_id_int = None
        else:
            user_id_int = None

        if user_id_int is not None:
            # 估算当前总月费，用于排序靠近的套餐
            from sqlalchemy import func

            stmt_budget = (
                select(func.coalesce(func.sum(Package.monthly_fee), 0.0))
                .join(UserPackage, UserPackage.package_id == Package.id)
                .where(
                    UserPackage.user_id == user_id_int,
                    *user_package_service.active_user_package_filters(),
                )
            )
            current_monthly = float(db.execute(stmt_budget).scalar_one())

            packages.sort(
                key=lambda p: abs(float(p.monthly_fee) - current_monthly)
            )
        else:
            packages.sort(key=lambda p: (not p.is_active, p.monthly_fee))

        return [_package_to_dict(p) for p in packages]
    finally:
        db.close()


async def recommend_package(user_id: str) -> dict:
    """
    基于用户用量历史和当前套餐性价比，推荐最适合的套餐。

    这里实现一个简化版本：
    - 使用最近 30 天总用量估算月流量需求
    - 使用当前生效套餐的月费作为预算参考
    - 调用 package_service.recommend_package 获取候选
    - 生成推荐理由和候选列表
    """
    db = SessionLocal()
    try:
        try:
            user_id_int = int(user_id)
        except ValueError:
            return {}

        # 最近 30 天数据总量
        from sqlalchemy import func

        stmt_usage = (
            select(func.coalesce(func.sum(UsageRecord.used_mb), 0.0))
            .where(UsageRecord.user_id == user_id_int)
        )
        total_mb_30d = float(db.execute(stmt_usage).scalar_one())
        avg_gb = total_mb_30d / 1024.0 if total_mb_30d > 0 else None

        # 当前月费
        stmt_budget = (
            select(func.coalesce(func.sum(Package.monthly_fee), 0.0))
            .join(UserPackage, UserPackage.package_id == Package.id)
            .where(
                UserPackage.user_id == user_id_int,
                *user_package_service.active_user_package_filters(),
            )
        )
        current_monthly = float(db.execute(stmt_budget).scalar_one())

        usage_data: dict[str, float] = {}
        if avg_gb is not None:
            usage_data["avg_monthly_used_gb"] = avg_gb
        if current_monthly:
            usage_data["max_monthly_budget"] = current_monthly

        candidates = package_service.recommend_package(
            db, user_id=user_id_int, usage_data=usage_data
        )

        if not candidates:
            return {}

        best = candidates[0]
        alternatives = candidates[1:3]

        # 简单估算节省金额：当前月费 - 推荐套餐月费
        saving = max(current_monthly - float(best.monthly_fee), 0.0)

        reason_parts = []
        if avg_gb is not None:
          reason_parts.append(
              f"你最近的月均流量约为 {avg_gb:.1f}GB"
          )
        if current_monthly:
          reason_parts.append(
              f"当前月费约 ¥{current_monthly:.0f}"
          )
        reason_core = "，".join(reason_parts) or "综合你的使用情况"
        reason = (
            f"{reason_core}，推荐你使用「{best.name}」，预计每月可节省约 ¥{saving:.0f}。"
        )

        result: dict = {
            "recommended": {
                "package_id": best.id,
                "name": best.name,
                "reason": reason,
                "saving": saving,
                "match_score": 95,
            },
            "alternatives": [
                {
                    "package_id": p.id,
                    "name": p.name,
                    "reason": "作为备选套餐，可以根据你对语音、短信等需求进一步选择。",
                    "match_score": 80,
                }
                for p in alternatives
            ],
        }
        return result
    finally:
        db.close()


async def get_package_detail(package_id: str) -> dict:
    """
    获取套餐详细信息，包含权益列表（当前从 benefits 关系简单映射名称）。
    """
    db = SessionLocal()
    try:
        try:
            package_id_int = int(package_id)
        except ValueError:
            return {}

        pkg = package_service.get_package_detail(db, package_id_int)
        if not pkg:
            return {}

        data = _package_to_dict(pkg)
        data["description"] = pkg.description
        data["benefits"] = [b.name for b in pkg.benefits]
        return data
    finally:
        db.close()


async def compare_packages(package_ids: List[str]) -> dict:
    """
    对比多个套餐的差异。

    返回结构示例：
    {
        "packages": [...],
        "fields": ["price", "data_gb", "voice_minutes", ...]
    }
    """
    if not package_ids:
        return {"packages": [], "fields": []}

    db = SessionLocal()
    try:
        int_ids: list[int] = []
        for pid in package_ids:
            try:
                int_ids.append(int(pid))
            except ValueError:
                continue

        if not int_ids:
            return {"packages": [], "fields": []}

        stmt = select(Package).where(Package.id.in_(int_ids))
        pkgs = db.execute(stmt).scalars().all()

        rows = []
        for p in pkgs:
            rows.append(
                {
                    "package_id": p.id,
                    "name": p.name,
                    "price": float(p.monthly_fee),
                    "data_gb": float(p.data_quota_gb),
                    "status": "active" if p.is_active else "inactive",
                }
            )

        fields = ["price", "data_gb", "status"]
        return {"packages": rows, "fields": fields}
    finally:
        db.close()
