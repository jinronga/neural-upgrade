from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Benefit, Package, User, UserBenefit, UserPackage
from app.services import benefit_service, usage_service, user_package_service


async def check_package_expiry(user_id: str) -> dict:
    """
    检查用户当前套餐是否即将到期。
    示例规则：
    - 按自然月计费：到当月最后一天视为“到期”
    - 剩余天数 <= 7 视为 expiring_soon
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {
            "expiring_soon": False,
            "reason": "invalid_user_id",
        }

    try:
        stmt = (
            select(UserPackage)
            .where(
                UserPackage.user_id == user_id_int,
                *user_package_service.active_user_package_filters(),
            )
            .order_by(UserPackage.start_date.desc())
        )
        current_up = db.execute(stmt).scalars().first()
        if not current_up or not current_up.package:
            return {
                "expiring_soon": False,
                "expire_date": None,
                "days_left": None,
                "auto_renew": False,
                "renew_amount": 0.0,
                "recommendation": "当前没有检测到在用套餐。",
            }

        today = date.today()
        year, month = today.year, today.month
        _, last_day = calendar.monthrange(year, month)
        expire_dt = date(year, month, last_day)
        days_left = max((expire_dt - today).days, 0)
        expiring_soon = days_left <= 7

        pkg: Package = current_up.package
        auto_renew = getattr(current_up, "auto_renew", False)
        renew_amount = float(pkg.monthly_fee)

        if expiring_soon:
            recommendation = "建议保持自动续费，或者提前评估是否需要升级/降级套餐。"
        else:
            recommendation = "当前距离账单日还有一段时间，如有需要可以提前规划下个月的套餐。"

        return {
            "expiring_soon": expiring_soon,
            "expire_date": expire_dt.isoformat(),
            "days_left": days_left,
            "auto_renew": bool(auto_renew),
            "renew_amount": renew_amount,
            "recommendation": recommendation,
        }
    finally:
        db.close()


async def calculate_renewal_offer(user_id: str) -> dict:
    """
    计算续费可享受的优惠（示例实现，重点在结构）。
    简单规则：
    - 在网时间 >= 12 个月且当前套餐为中高档：提供“续费送流量”优惠
    - 否则返回 has_offer=False
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"has_offer": False}

    try:
        stmt = (
            select(UserPackage)
            .where(
                UserPackage.user_id == user_id_int,
                *user_package_service.active_user_package_filters(),
            )
            .order_by(UserPackage.start_date.asc())
        )
        first_up = db.execute(stmt).scalars().first()
        if not first_up or not first_up.package:
            return {"has_offer": False}

        on_net_days = (date.today() - first_up.start_date.date()).days
        on_net_months = on_net_days // 30

        pkg: Package = first_up.package
        price = float(pkg.monthly_fee)

        if on_net_months >= 12 and price >= 39:
            saving = 120  # 示例：6 个月共赠送 2GB/月 × 6 × 单价 10 元
            return {
                "has_offer": True,
                "offer_type": "续费送流量",
                "description": "连续续费6个月当前套餐，每月额外赠送 2GB 流量。",
                "saving": saving,
                "requirements": "当前套餐已连续使用满 12 个月且无欠费记录。",
            }

        return {
            "has_offer": False,
            "offer_type": None,
            "description": "当前暂无专属续费优惠，后续活动将通过短信或App通知你。",
            "saving": 0,
            "requirements": None,
        }
    finally:
        db.close()


async def generate_renewal_message(user_id: str) -> str:
    """
    生成个性化的续费提醒文案。
    综合套餐到期时间、续费优惠、以及当前用量情况（流量阈值）。
    """
    expiry = await check_package_expiry(user_id)
    offer = await calculate_renewal_offer(user_id)

    from app.agent.functions.usage_functions import check_usage_threshold

    threshold = await check_usage_threshold(user_id)

    if not expiry.get("expire_date"):
        return "目前未检测到正在生效的套餐，如有需要可以让我帮你选择并办理一个新套餐。"

    days_left = expiry.get("days_left", 0)
    expiring_soon = expiry.get("expiring_soon", False)
    auto_renew = expiry.get("auto_renew", False)
    renew_amount = float(expiry.get("renew_amount", 0.0))

    parts: list[str] = []
    parts.append(
        f"你的当前套餐预计在 {expiry['expire_date']} 到期，距离账单日还有 {days_left} 天。"
    )

    if auto_renew:
        parts.append(
            f"当前已开启自动续费，届时将以 ¥{renew_amount:.0f} 的价格自动续费一个月。"
        )
    else:
        parts.append(
            f"当前未开启自动续费，如需继续使用，可以在账单日前手动续费（约 ¥{renew_amount:.0f}/月）。"
        )

    if offer.get("has_offer"):
        parts.append(
            f"你有一个专属续费优惠：{offer['description']}，预计可为你节省约 ¥{offer['saving']:.0f}。"
        )

    if threshold.get("has_warning"):
        parts.append(
            "另外，本月流量使用已经接近套餐上限，建议适当关注用量或考虑升级到更高档次套餐。"
        )

    if not offer.get("has_offer") and not threshold.get("has_warning") and not expiring_soon:
        parts.append("整体来看，目前的套餐和使用习惯比较匹配，可以继续稳定使用。")

    return " ".join(parts)


async def daily_expiry_check() -> dict:
    """
    每天凌晨执行，检查 3 天内过期的权益并返回统计结果。
    实际推送逻辑应集成短信/站内信，这里仅返回结构以供日志或后续处理。
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        three_days_later = now + timedelta(days=3)

        stmt = (
            select(UserBenefit)
            .where(
                UserBenefit.status == "active",
                UserBenefit.expires_at.is_not(None),
                UserBenefit.expires_at <= three_days_later,
            )
        )
        records = db.execute(stmt).scalars().all()
        affected_users = {ub.user_id for ub in records}

        return {
            "checked_at": now.isoformat(),
            "expiring_benefits_count": len(records),
            "affected_users_count": len(affected_users),
        }
    finally:
        db.close()


async def monthly_benefit_grant() -> dict:
    """
    每月 1 日给所有活跃用户发放当月权益。
    实际逻辑委托给 benefit_service.monthly_grant。
    """
    db = SessionLocal()
    try:
        created_count = benefit_service.monthly_grant(db)
        return {
            "granted_count": created_count,
            "run_at": datetime.now().isoformat(),
        }
    finally:
        db.close()


async def threshold_check_cron() -> dict:
    """
    每 5 分钟检查用量超过 80% 的用户，发送预警（示例统计）。
    实际发送由外部系统完成，这里只返回检测到的用户数量。
    """
    db = SessionLocal()
    try:
        # 简化：遍历所有 active 用户套餐，检查流量使用百分比
        stmt = select(UserPackage.user_id).where(
            *user_package_service.active_user_package_filters()
        )
        user_ids = {row[0] for row in db.execute(stmt)}

        from app.agent.functions.usage_functions import get_realtime_usage

        high_usage_users: List[int] = []
        for uid in user_ids:
            usage = await get_realtime_usage(str(uid))
            data = usage.get("data", {})
            percent_used = float(data.get("percent", 0.0))
            if percent_used >= 80.0:
                high_usage_users.append(uid)

        return {
            "run_at": datetime.now().isoformat(),
            "checked_users": len(user_ids),
            "high_usage_users": len(high_usage_users),
        }
    finally:
        db.close()
