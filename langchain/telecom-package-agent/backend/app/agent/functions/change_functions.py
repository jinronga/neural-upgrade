from __future__ import annotations

import calendar
import random
from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Package, UserPackage
from app.services import package_service


async def estimate_upgrade_cost(user_id: str, target_package_id: str) -> dict:
    """保留的简单估价函数，供旧调用方使用。"""
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


async def check_change_eligibility(user_id: str, target_package_id: str) -> dict:
    """
    检查用户是否有资格变更到目标套餐。

    示例规则：
    - 至少存在一个 active 套餐（否则视为新办，默认可办理）
    - 当前套餐使用时长 >= 1 个月
    - 无欠费（此处简单假设无欠费，可后续接入计费系统）
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
        target_id_int = int(target_package_id)
    except ValueError:
        return {
            "eligible": False,
            "reason": "用户编号或套餐编号格式不正确。",
            "constraints": {},
        }

    try:
        target_pkg = db.get(Package, target_id_int)
        if not target_pkg or not target_pkg.is_active:
            return {
                "eligible": False,
                "reason": "目标套餐不存在或暂不可办理。",
                "constraints": {},
            }

        stmt = (
            select(UserPackage)
            .where(
                UserPackage.user_id == user_id_int,
                UserPackage.status == "active",
            )
            .order_by(UserPackage.start_date.desc())
        )
        current_up = db.execute(stmt).scalars().first()
        if not current_up:
            # 无当前套餐，视为新办，默认允许
            return {
                "eligible": True,
                "reason": None,
                "constraints": {
                    "min_usage_months": 0,
                    "current_package_status": "none",
                    "overdue_bills": False,
                },
            }

        start_date = current_up.start_date.date()
        months_used = max((date.today() - start_date).days // 30, 0)
        overdue_bills = False  # 占位：真实实现应接入计费系统

        eligible = months_used >= 1 and not overdue_bills
        reason = None
        if not eligible:
            if overdue_bills:
                reason = "当前存在未结清话费，请先完成缴费再办理套餐变更。"
            else:
                reason = "当前套餐使用未满 1 个月，暂不支持变更，建议下个账期再尝试。"

        return {
            "eligible": eligible,
            "reason": reason,
            "constraints": {
                "min_usage_months": 1,
                "current_package_status": current_up.status,
                "overdue_bills": overdue_bills,
            },
        }
    finally:
        db.close()


async def calculate_change_cost(user_id: str, target_package_id: str) -> dict:
    """
    计算套餐变更的差价和资源结转。

    说明：当前实现为示例，重点在返回结构，方便 Agent 生成解释性文案。
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
        target_id_int = int(target_package_id)
    except ValueError:
        return {}

    try:
        # 当前套餐
        stmt = (
            select(UserPackage)
            .where(
                UserPackage.user_id == user_id_int,
                UserPackage.status == "active",
            )
            .order_by(UserPackage.start_date.desc())
        )
        current_up = db.execute(stmt).scalars().first()
        if not current_up or not current_up.package:
            return {}

        current_pkg = current_up.package
        target_pkg = db.get(Package, target_id_int)
        if not target_pkg:
            return {}

        from_price = float(current_pkg.monthly_fee)
        to_price = float(target_pkg.monthly_fee)

        if to_price > from_price:
            change_type = "upgrade"
            effective_date = "即时生效"
        elif to_price < from_price:
            change_type = "downgrade"
            effective_date = "次月生效"
        else:
            change_type = "same"
            effective_date = "下个账期生效"

        today = date.today()
        total_days = calendar.monthrange(today.year, today.month)[1]
        days_remaining = max(total_days - today.day + 1, 0)
        fraction = days_remaining / total_days if total_days else 0.0

        # 假设流量/语音资源以当前套餐配置为基准
        data_original = float(current_pkg.data_quota_gb)
        data_carryover = round(data_original * fraction, 1)
        data_formula = (
            f"{data_original:.1f} × ({days_remaining}天/{total_days}天)"
            f" = {data_carryover:.1f}GB"
        )

        voice_original = 500.0
        voice_carryover = round(voice_original * fraction)
        voice_formula = (
            f"{voice_original:.0f} × ({days_remaining}/{total_days})"
            f" = {voice_carryover:.0f}分钟"
        )

        amount = round(to_price - from_price, 2)
        if change_type == "upgrade" and amount > 0:
            pro_rated = round(amount * fraction, 2)
        else:
            pro_rated = 0.0
        total_to_pay = max(pro_rated, 0.0)

        # 已领/未领权益和新权益：目前无明细表，先用占位信息
        benefit_changes = {
            "current_month_claimed": ["腾讯视频VIP"],
            "current_month_pending": ["咖啡券"],
            "pending_disposition": "可折算为 200 积分或延续到新套餐中。",
            "new_benefits": ["爱奇艺VIP", "云空间50G"],
        }

        return {
            "from_package": {
                "name": current_pkg.name,
                "price": from_price,
            },
            "to_package": {
                "name": target_pkg.name,
                "price": to_price,
            },
            "change_type": change_type,
            "effective_date": effective_date,
            "data_carryover": {
                "original": data_original,
                "carryover": data_carryover,
                "formula": data_formula,
            },
            "voice_carryover": {
                "original": voice_original,
                "carryover": voice_carryover,
                "formula": voice_formula,
            },
            "price_diff": {
                "amount": amount,
                "pro_rated": pro_rated,
                "total_to_pay": total_to_pay,
            },
            "benefit_changes": benefit_changes,
        }
    finally:
        db.close()


async def submit_change_request(
    user_id: str, target_package_id: str, confirm: bool = False
) -> dict:
    """
    提交套餐变更申请。

    当前实现不落库，仅生成一个模拟的变更记录结构，方便 Agent 解释下一步操作。
    """
    cost_info = await calculate_change_cost(user_id, target_package_id)
    if not cost_info:
        return {
            "success": False,
            "status": "rejected",
            "message": "暂时无法计算变更费用，请稍后再试或联系人工客服。",
        }

    price_diff = cost_info.get("price_diff", {})
    total_to_pay = float(price_diff.get("total_to_pay", 0.0))
    payment_required = total_to_pay > 0

    today = datetime.now()
    payment_deadline_dt = today + timedelta(days=1)
    effective_date = (
        today.date().isoformat()
        if cost_info.get("change_type") == "upgrade"
        else (today.replace(day=1) + timedelta(days=32)).replace(day=1).date().isoformat()
    )

    change_id = f"CHG{today.strftime('%Y%m%d')}{random.randint(1000,9999)}"

    status = "pending_payment" if payment_required else "approved"
    next_steps = (
        f"请在 {payment_deadline_dt.strftime('%Y-%m-%d %H:%M:%S')} 前支付 ¥{total_to_pay:.2f} 差价，"
        "支付成功后新套餐将即时生效。"
        if payment_required
        else "系统将为你在约定时间自动切换至新套餐。"
    )

    if not confirm:
        # 如果未确认，仅返回预览信息
        return {
            "success": True,
            "preview": True,
            "change_id": change_id,
            "status": status,
            "payment_required": payment_required,
            "payment_amount": total_to_pay,
            "payment_deadline": payment_deadline_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "effective_date": effective_date,
            "next_steps": next_steps,
        }

    # 真正提交（当前为示例，未写入数据库）
    return {
        "success": True,
        "preview": False,
        "change_id": change_id,
        "status": status,
        "payment_required": payment_required,
        "payment_amount": total_to_pay,
        "payment_deadline": payment_deadline_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "effective_date": effective_date,
        "next_steps": next_steps,
    }


async def get_change_history(user_id: str, limit: int = 5) -> List[dict]:
    """
    查询用户的套餐变更历史。

    当前实现为占位：返回空列表或简单示例结构，后续可接入真实变更记录表。
    """
    try:
        int(user_id)
    except ValueError:
        return []

    # TODO: 接入真实变更记录表
    return []


async def cancel_change_request(change_id: str) -> dict:
    """
    取消待支付的变更申请。

    当前实现为占位，假设仅支持取消状态为 pending_payment 的申请。
    """
    if not change_id:
        return {"success": False, "reason": "invalid_change_id"}

    # TODO: 在接入真实表后，根据 change_id 更新状态
    return {
        "success": True,
        "change_id": change_id,
        "status": "cancelled",
        "message": "已为你取消本次套餐变更申请，如需重新办理可以随时告诉我。",
    }

