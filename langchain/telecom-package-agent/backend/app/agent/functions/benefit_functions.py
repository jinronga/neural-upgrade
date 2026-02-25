from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import List

from app.database import SessionLocal
from app.models import Benefit, User
from app.services import benefit_service, user_service


def _infer_type_and_icon(name: str) -> tuple[str, str]:
    n = name.lower()
    if "腾讯" in name or "视频" in name or "vip" in n:
        return "video_vip", "🎬"
    if "星巴克" in name or "咖啡" in name:
        return "coffee_coupon", "☕"
    if "外卖" in name or "饿了么" in name or "美团" in name:
        return "food_coupon", "🍔"
    return "generic", "🎁"


async def get_pending_benefits(user_id: str) -> List[dict]:
    """
    查询用户待领取的权益，返回带有过期信息和紧急程度的列表。
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return []

    try:
        benefits = benefit_service.get_pending_benefits(db, user_id_int)
        now = datetime.now()
        results: List[dict] = []
        for b in benefits:
            b: Benefit
            b_type, icon = _infer_type_and_icon(b.name)
            # 简单规则：从创建时间起 30 天过期（若无创建时间，则从现在起算）
            created_at = getattr(b, "created_at", None) or now
            expire_dt = created_at + timedelta(days=30)
            days_left = max((expire_dt.date() - date.today()).days, 0)
            is_urgent = days_left <= 3

            recommend_reason = None
            if b_type == "video_vip":
                recommend_reason = "你近期的视频内容消费较多，开通会员能带来更好的体验。"
            elif b_type == "coffee_coupon":
                recommend_reason = "适合下午或周末小憩时使用，为生活增加一点仪式感。"

            results.append(
                {
                    "benefit_id": f"BENEFIT_{b.id}",
                    "name": b.name,
                    "type": b_type,
                    "icon": icon,
                    "description": b.description,
                    "expire_time": expire_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "days_left": days_left,
                    "is_urgent": is_urgent,
                    "inventory": b.inventory,
                    "is_active": b.is_active,
                    "recommend_reason": recommend_reason,
                }
            )
        return results
    finally:
        db.close()


async def recommend_benefit_to_claim(user_id: str) -> dict:
    """
    根据用户行为和权益紧急程度推荐最适合领取的权益。
    当前实现：
    - 优先选择 is_urgent=True 的权益
    - 其次选择库存较紧张的权益
    - 再根据权益类型与当前时间组合生成推荐理由
    """
    pending = await get_pending_benefits(user_id)
    if not pending:
        return {}

    urgent = [b for b in pending if b.get("is_urgent")]
    candidates = urgent or pending

    # 按库存从少到多排序（库存越少越优先）
    candidates.sort(key=lambda x: x.get("inventory", 0))
    chosen = candidates[0]

    name = chosen["name"]
    b_type = chosen.get("type", "generic")
    inventory = chosen.get("inventory", 0)

    now = datetime.now()
    hour = now.hour

    reason_parts: list[str] = []
    if b_type == "video_vip":
        reason_parts.append("你最近有较多在线观看视频场景，视频会员能带来更好的体验")
        if 19 <= hour <= 23:
            reason_parts.append("现在是晚间休闲时间，适合边看剧边使用该权益")
    elif b_type == "coffee_coupon":
        reason_parts.append("咖啡类权益适合下午或周末外出时使用")
        if 13 <= hour <= 17:
            reason_parts.append("当前正值下午时段，正好可以用一杯咖啡提神")

    if chosen.get("is_urgent"):
        reason_parts.append("该权益即将过期，建议优先领取避免浪费")

    if inventory and inventory < 50:
        reason_parts.append("库存偏紧，后续可能会抢不到")

    if not reason_parts:
        reason_parts.append("该权益综合来看性价比较高，适合当前的你")

    reason = "，".join(reason_parts)

    confidence = 0.9
    if chosen.get("is_urgent"):
        confidence += 0.03
    if b_type in {"video_vip", "coffee_coupon"}:
        confidence += 0.02

    return {
        "benefit_id": chosen["benefit_id"],
        "name": name,
        "reason": reason,
        "confidence": round(min(confidence, 0.99), 2),
    }


async def claim_benefit(
    user_id: str, benefit_id: str, channel: str = "agent"
) -> dict:
    """
    领取指定权益。
    根据权益类型返回不同的交付方式：
    - api_direct：直接充值到账号
    - card_password：返回卡密信息
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
        benefit_id_str = str(benefit_id)
        if benefit_id_str.startswith("BENEFIT_"):
            benefit_id_int = int(benefit_id_str.replace("BENEFIT_", ""))
        else:
            benefit_id_int = int(benefit_id_str)
    except ValueError:
        return {"success": False, "reason": "invalid_ids"}

    try:
        benefit = db.get(Benefit, benefit_id_int)
        if not benefit:
            return {"success": False, "reason": "benefit_not_found"}

        record = benefit_service.claim_benefit(
            db, user_id=user_id_int, benefit_id=benefit_id_int, channel=channel
        )
        if record is None:
            return {"success": False, "reason": "claim_failed"}

        b_type, _ = _infer_type_and_icon(benefit.name)
        today = date.today()
        expire_time = (today + timedelta(days=30)).isoformat()

        if b_type == "video_vip":
            masked_account = "你的手机号码"
            return {
                "success": True,
                "delivery_type": "api_direct",
                "message": f"已为你开通 {benefit.name}，权益将在几分钟内生效。",
                "account": masked_account,
                "expire_time": expire_time,
            }

        if b_type == "coffee_coupon":
            card_no = f"CARD{random.randint(100000, 999999)}"
            password = f"PWD{random.randint(100000, 999999)}"
            instructions = "打开商家 App，在“我的-兑换”中输入卡密完成使用。"
            return {
                "success": True,
                "delivery_type": "card_password",
                "card_no": card_no,
                "password": password,
                "qr_code": "BASE64_QR_PLACEHOLDER",
                "expire_time": expire_time,
                "instructions": instructions,
            }

        return {
            "success": True,
            "delivery_type": "api_direct",
            "message": f"已为你发放「{benefit.name}」，具体使用方式可在权益中心查看详情。",
            "account": "你的账号",
            "expire_time": expire_time,
        }
    finally:
        db.close()


async def claim_all_benefits(user_id: str) -> dict:
    """
    一键领取所有待领权益。
    """
    pending = await get_pending_benefits(user_id)
    if not pending:
        return {"success_count": 0, "failed_count": 0, "results": []}

    results: List[dict] = []
    success_count = 0
    failed_count = 0

    for b in pending:
        res = await claim_benefit(user_id, b["benefit_id"], channel="agent_batch")
        ok = bool(res.get("success"))
        if ok:
            success_count += 1
        else:
            failed_count += 1

        results.append(
            {
                "benefit_id": b["benefit_id"],
                "success": ok,
                "message": res.get("message") or res.get("reason", ""),
            }
        )

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }


async def compensate_expired_benefit(user_id: str, benefit_id: str) -> dict:
    """
    过期权益补领（根据用户价值决定是否收费）。

    规则示例：
    - 年价值 >= 2000：free
    - 年价值 >= 800：points（默认 200 积分）
    - 否则：pay（建议付费或联系客服）
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"can_compensate": False, "method": "pay", "message": "用户编号无效"}

    try:
        user = db.get(User, user_id_int)
        if not user:
            return {"can_compensate": False, "method": "pay", "message": "未找到该用户信息"}

        estimated_value = user_service.get_user_value(db, user_id_int)
        user_points = int(estimated_value / 5)

        if estimated_value >= 2000:
            return {
                "can_compensate": True,
                "method": "free",
                "points_needed": 0,
                "user_points": user_points,
                "message": "作为高价值用户，本次过期权益可为你免费补发。",
            }

        if estimated_value >= 800:
            points_needed = 200
            if user_points >= points_needed:
                return {
                    "can_compensate": True,
                    "method": "points",
                    "points_needed": points_needed,
                    "user_points": user_points,
                    "message": f"扣除 {points_needed} 积分即可补发该权益。",
                }
            return {
                "can_compensate": False,
                "method": "points",
                "points_needed": points_needed,
                "user_points": user_points,
                "message": "当前积分不足，暂无法通过积分补发该权益。",
            }

        return {
            "can_compensate": False,
            "method": "pay",
            "points_needed": None,
            "user_points": user_points,
            "message": "该权益暂不支持免费补发，如有需要可咨询人工客服了解付费补开方案。",
        }
    finally:
        db.close()


async def check_benefit_inventory(benefit_id: str) -> dict:
    """
    检查权益库存情况。
    """
    db = SessionLocal()
    try:
        benefit_id_str = str(benefit_id)
        if benefit_id_str.startswith("BENEFIT_"):
            benefit_id_int = int(benefit_id_str.replace("BENEFIT_", ""))
        else:
            benefit_id_int = int(benefit_id_str)
    except ValueError:
        return {"found": False, "reason": "invalid_benefit_id"}

    try:
        benefit = db.get(Benefit, benefit_id_int)
        if not benefit:
            return {"found": False, "reason": "not_found"}

        inventory = benefit.inventory
        status = "normal"
        if inventory <= 0:
            status = "sold_out"
        elif inventory < 50:
            status = "tight"

        return {
            "found": True,
            "benefit_id": f"BENEFIT_{benefit.id}",
            "name": benefit.name,
            "inventory": inventory,
            "status": status,
        }
    finally:
        db.close()

