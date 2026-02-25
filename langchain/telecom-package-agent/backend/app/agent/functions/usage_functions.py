from __future__ import annotations

import calendar
from collections import Counter
from datetime import date, datetime, timedelta
from typing import List

import redis
from sqlalchemy import func, select

from app.core.config import settings
from app.database import SessionLocal
from app.models import Package, UsageRecord, UserPackage
from app.services import usage_service


async def get_current_usage(user_id: str) -> dict:
    """Simple wrapper for current usage (total MB)."""
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {}

    try:
        total_mb = usage_service.get_current_usage(
            db, user_id_int, redis_client=None
        )
        return {"user_id": user_id_int, "total_used_mb": total_mb}
    finally:
        db.close()


async def get_usage_history(user_id: str, months: int = 6) -> List[dict]:
    """Return usage history records for the last N months."""
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return []

    try:
        records = usage_service.get_usage_history(
            db, user_id_int, months=months
        )
        return [
            {
                "id": r.id,
                "record_time": r.record_time.isoformat(),
                "used_mb": float(r.used_mb),
            }
            for r in records
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1. 实时用量查询（带缓存）
# ---------------------------------------------------------------------------


async def get_realtime_usage(user_id: str) -> dict:
    """
    查询用户实时用量（带缓存，5分钟过期）。
    返回数据结构见提示说明。
    """
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {}

    cache_key = f"user:{user_id_int}:realtime_usage"
    client = redis.from_url(settings.REDIS_URL)

    cached = client.get(cache_key)
    if cached:
        try:
            import json

            return json.loads(cached)
        except Exception:
            pass

    db = SessionLocal()
    try:
        # 数据流量使用（MB）
        total_mb = usage_service.get_current_usage(
            db, user_id_int, redis_client=None
        )

        # 从当前套餐推断配额（如果存在）
        pkg_stmt = (
            select(Package)
            .join(UserPackage, UserPackage.package_id == Package.id)
            .where(
                UserPackage.user_id == user_id_int,
                UserPackage.status == "active",
            )
        )
        current_pkg = db.execute(pkg_stmt).scalars().first()

        data_total_gb = float(current_pkg.data_quota_gb) if current_pkg else 60.0
        data_used_gb = float(total_mb) / 1024.0
        data_remaining_gb = max(data_total_gb - data_used_gb, 0.0)
        data_percent = (
            (data_used_gb / data_total_gb * 100.0) if data_total_gb > 0 else 0.0
        )

        # 语音 / 短信目前缺少明细，简单用套餐资源和 0 使用值占位
        voice_total = 500.0
        voice_used = 0.0
        voice_percent = 0.0

        sms_total = 100.0
        sms_used = 0.0
        sms_percent = 0.0

        # 账单周期：假设按自然月，计算剩余天数
        today = date.today()
        _, last_day = calendar.monthrange(today.year, today.month)
        end_date = date(today.year, today.month, last_day)
        days_remaining = max((end_date - today).days, 0)

        # 最近 30 天平均每日流量（GB）
        now = datetime.utcnow()
        since = now - timedelta(days=30)
        usage_stmt = (
            select(func.coalesce(func.sum(UsageRecord.used_mb), 0.0))
            .where(
                UsageRecord.user_id == user_id_int,
                UsageRecord.record_time >= since,
            )
        )
        total_mb_30d = float(db.execute(usage_stmt).scalar_one())
        daily_avg_gb = (total_mb_30d / 1024.0 / 30.0) if total_mb_30d > 0 else 0.0

        # 简单统计高频使用时段（按小时）
        hours_stmt = (
            select(
                func.extract("hour", UsageRecord.record_time).label("hh"),
                func.sum(UsageRecord.used_mb).label("sum_mb"),
            )
            .where(UsageRecord.user_id == user_id_int)
            .group_by("hh")
            .order_by(func.sum(UsageRecord.used_mb).desc())
            .limit(3)
        )
        rows = db.execute(hours_stmt).all()
        peak_hours = [
            f"{int(r.hh):02d}:00"  # type: ignore[attr-defined]
            for r in rows
        ]

        result = {
            "data": {
                "used": round(data_used_gb, 2),
                "total": round(data_total_gb, 2),
                "percent": round(data_percent, 1),
                "remaining": round(data_remaining_gb, 2),
                "unit": "GB",
            },
            "voice": {
                "used": round(voice_used, 0),
                "total": round(voice_total, 0),
                "percent": round(voice_percent, 1),
                "remaining": round(voice_total - voice_used, 0),
                "unit": "分钟",
            },
            "sms": {
                "used": round(sms_used, 0),
                "total": round(sms_total, 0),
                "percent": round(sms_percent, 1),
                "remaining": round(sms_total - sms_used, 0),
                "unit": "条",
            },
            "days_remaining": days_remaining,
            "daily_avg": round(daily_avg_gb, 2),
            "estimated_end": end_date.isoformat(),
            "peak_hours": peak_hours,
        }

        # 缓存 5 分钟
        try:
            import json

            client.setex(cache_key, 300, json.dumps(result, ensure_ascii=False))
        except Exception:
            pass

        return result
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. 用量趋势分析
# ---------------------------------------------------------------------------


async def get_usage_trend(user_id: str, days: int = 30) -> dict:
    """
    获取用量趋势分析：
    - trend: increasing/stable/decreasing
    - growth_rate: 环比增长率
    - peak_days: 高峰星期
    - peak_hours: 高峰时段
    """
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {}

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        since = now - timedelta(days=days)
        stmt = (
            select(UsageRecord.record_time, UsageRecord.used_mb)
            .where(
                UsageRecord.user_id == user_id_int,
                UsageRecord.record_time >= since,
            )
        )
        records = db.execute(stmt).all()

        if not records:
            return {
                "trend": "stable",
                "growth_rate": 0.0,
                "peak_days": [],
                "peak_hours": [],
                "recommendation": "最近没有明显的用量记录。",
            }

        # 按天聚合
        daily = {}
        for rec_time, used_mb in records:
            day_key = rec_time.date().isoformat()  # type: ignore[union-attr]
            daily[day_key] = daily.get(day_key, 0.0) + float(used_mb)

        ordered_days = sorted(daily.keys())
        n = len(ordered_days)
        if n < 4:
            # 数据较少，简单给出提示
            total_mb = sum(daily.values())
            return {
                "trend": "stable",
                "growth_rate": 0.0,
                "peak_days": [],
                "peak_hours": [],
                "recommendation": f"最近用量总计约 {total_mb/1024:.1f}GB，暂无明显趋势。",
            }

        half = n // 2
        first_avg = sum(daily[d] for d in ordered_days[:half]) / half
        last_avg = sum(daily[d] for d in ordered_days[half:]) / (n - half)

        if first_avg == 0:
            growth_rate = 0.0
        else:
            growth_rate = (last_avg - first_avg) / first_avg

        if growth_rate > 0.1:
            trend = "increasing"
        elif growth_rate < -0.1:
            trend = "decreasing"
        else:
            trend = "stable"

        # 高频星期与时段
        weekday_counter = Counter()
        hour_counter = Counter()
        for rec_time, used_mb in records:
            dt = rec_time  # type: ignore[assignment]
            weekday_counter[dt.weekday()] += float(used_mb)
            hour_counter[dt.hour] += float(used_mb)

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        peak_days = [
            weekday_names[w]
            for w, _ in weekday_counter.most_common(2)
        ]

        top_hours = [h for h, _ in hour_counter.most_common(2)]
        peak_hours: list[str] = []
        for h in top_hours:
            start = f"{h:02d}:00"
            end = f"{(h+1)%24:02d}:00"
            peak_hours.append(f"{start}-{end}")

        if trend == "increasing":
            recommendation = "你的流量使用呈上升趋势，建议关注高峰时段，必要时可考虑升级套餐或购买加油包。"
        elif trend == "decreasing":
            recommendation = "你的流量使用呈下降趋势，可以适当下调套餐档位以节省费用。"
        else:
            recommendation = "你的流量使用相对稳定，可继续观察，按需调整套餐。"

        return {
            "trend": trend,
            "growth_rate": round(growth_rate, 3),
            "peak_days": peak_days,
            "peak_hours": peak_hours,
            "recommendation": recommendation,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. 超额预警检查
# ---------------------------------------------------------------------------


async def check_usage_threshold(user_id: str) -> dict:
    """
    检查是否接近套餐阈值，主要关注流量。
    """
    realtime = await get_realtime_usage(user_id)
    if not realtime:
        return {"has_warning": False, "warnings": [], "need_alert": False}

    warnings: list[dict] = []

    data = realtime.get("data", {})
    data_percent = float(data.get("percent", 0.0))
    data_remaining = float(data.get("remaining", 0.0))

    if data_percent >= 90.0:
        warnings.append(
            {
                "type": "data",
                "used_percent": round(data_percent, 1),
                "remaining": round(data_remaining, 2),
                "suggestion": "你的本月流量已接近用完，建议购买 5GB 加油包，仅需约 10 元，避免降速或额外收费。",
            }
        )

    need_alert = bool(warnings)
    return {"has_warning": need_alert, "warnings": warnings, "need_alert": need_alert}


# ---------------------------------------------------------------------------
# 4. 加油包推荐（简单示例）
# ---------------------------------------------------------------------------


async def recommend_topup(user_id: str, need_gb: float | None = None) -> dict:
    """
    推荐合适的加油包。
    使用静态加油包列表做示例，可后续接真实产品库。
    """
    realtime = await get_realtime_usage(user_id)
    data = realtime.get("data", {}) if realtime else {}

    if need_gb is None:
        total = float(data.get("total", 0.0))
        used = float(data.get("used", 0.0))
        remaining = max(total - used, 0.0)
        # 目标为至少再保证 30% 总量
        need_gb = max(total * 0.3 - remaining, 1.0)

    catalog = [
        {"package_id": "TOPUP_1GB", "name": "1GB 加油包", "price": 5.0, "valid_days": 30},
        {"package_id": "TOPUP_5GB", "name": "5GB 加油包", "price": 10.0, "valid_days": 30},
        {"package_id": "TOPUP_10GB", "name": "10GB 加油包", "price": 18.0, "valid_days": 30},
        {"package_id": "TOPUP_20GB", "name": "20GB 加油包", "price": 30.0, "valid_days": 30},
    ]

    # 找到容量上覆盖 need_gb 且价格相对友好的加油包
    sorted_catalog = sorted(catalog, key=lambda x: x["price"])
    recommended = None
    for item in sorted_catalog:
        size = float(item["name"].split("GB")[0])
        if size >= need_gb:
            recommended = item
            break
    if recommended is None:
        recommended = sorted_catalog[-1]

    # 简单估算节省金额：假设单独买流量单价为 3 元/GB
    size = float(recommended["name"].split("GB")[0])
    market_price = size * 3.0
    saving = max(market_price - recommended["price"], 0.0)

    alternatives = [item for item in sorted_catalog if item is not recommended][:2]

    return {
        "recommended": {
            **recommended,
            "saving": round(saving, 1),
        },
        "alternatives": alternatives,
    }


# ---------------------------------------------------------------------------
# 5. 生成用量报告
# ---------------------------------------------------------------------------


async def generate_usage_report(user_id: str, month: str | None = None) -> str:
    """
    生成用户友好的用量报告（自然语言）。
    month: "YYYY-MM"，默认为当前月份。
    """
    try:
        user_id_int = int(user_id)
    except ValueError:
        return "暂时无法生成用量报告，因为用户编号格式不正确。"

    if month is None:
        today = date.today()
        month = f"{today.year:04d}-{today.month:02d}"

    year, mon = month.split("-")
    year_i = int(year)
    mon_i = int(mon)
    _, last_day = calendar.monthrange(year_i, mon_i)
    start_dt = datetime(year_i, mon_i, 1)
    end_dt = datetime(year_i, mon_i, last_day, 23, 59, 59)

    db = SessionLocal()
    try:
        stmt = (
            select(UsageRecord.record_time, UsageRecord.used_mb)
            .where(
                UsageRecord.user_id == user_id_int,
                UsageRecord.record_time >= start_dt,
                UsageRecord.record_time <= end_dt,
            )
        )
        rows = db.execute(stmt).all()
        if not rows:
            return f"{month} 期间未查询到你的流量使用记录。"

        total_mb = sum(float(r.used_mb) for r in rows)
        total_gb = total_mb / 1024.0

        # 按日统计
        daily = {}
        for rec_time, used_mb in rows:
            day_key = rec_time.date().isoformat()  # type: ignore[union-attr]
            daily[day_key] = daily.get(day_key, 0.0) + float(used_mb)

        ordered_days = sorted(daily.keys())
        avg_daily_gb = (total_gb / len(ordered_days)) if ordered_days else 0.0

        # 高峰日 & 高峰时段
        weekday_counter = Counter()
        hour_counter = Counter()
        for rec_time, used_mb in rows:
            dt = rec_time  # type: ignore[assignment]
            weekday_counter[dt.weekday()] += float(used_mb)
            hour_counter[dt.hour] += float(used_mb)

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        peak_day = weekday_names[weekday_counter.most_common(1)[0][0]]
        peak_hour = hour_counter.most_common(1)[0][0]
        peak_hour_range = f"{peak_hour:02d}:00-{(peak_hour+1)%24:02d}:00"

        report_lines = [
            f"【{month} 用量报告】",
            f"本月截至目前，你共使用了约 {total_gb:.1f}GB 流量，平均每天约 {avg_daily_gb:.2f}GB。",
            f"从使用分布来看，你在{peak_day}使用流量最多，高峰时段主要集中在 {peak_hour_range}。",
            "总体来看，你的用量水平属于正常范围，建议在高峰时段留意 App 后台流量，避免无感知消耗。",
        ]

        return "\n".join(report_lines)
    finally:
        db.close()


