from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List

from app.core.config import settings
from app.database import SessionLocal
from app.models import Complaint, User
from app.services import user_service
from langchain.chat_models import ChatOpenAI


async def classify_complaint(message: str) -> dict:
    """
    使用 LLM 对投诉内容进行类型与情绪识别。
    """
    prompt = f"""
你是运营商客服的智能质检助手。你的任务是分析用户的一段投诉或问题描述，并用 JSON 给出结构化结果。

用户投诉内容：
{message}

请只返回一个 JSON 对象（不要额外解释），格式如下：
{{
  "type": "network_slow" | "overcharge" | "benefit_missing" | "signal_issue" | "other",
  "sub_type": "indoor_signal" | "outdoor_signal" | "video_buffering" | "billing_detail" | "",
  "sentiment": "angry" | "neutral" | "sad",
  "urgency": "high" | "medium" | "low",
  "keywords": ["从用户话语中提取的关键投诉词"],
  "need_human": true | false
}}

判断逻辑建议：
- 当用户包含明显负面词汇（如“气死我了”“太差了”“投诉”“坑”等）或多次强调影响严重时，sentiment 多为 "angry"，urgency 至少 "medium"。
- 当 sentiment 为 "angry" 且投诉涉及扣费错误或网络长期无法使用时，建议 need_human 为 true。
"""
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.0,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    import json

    try:
        resp = await llm.ainvoke(prompt)
        text = str(resp.content).strip()
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {
        "type": "other",
        "sub_type": "",
        "sentiment": "neutral",
        "urgency": "medium",
        "keywords": [],
        "need_human": False,
    }


async def diagnose_network_issue(user_id: str) -> dict:
    """
    诊断用户网络问题（示例实现，核心是结构）。
    """
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"has_issue": False, "reason": "invalid_user_id"}

    # 真实环境应通过基站监控/工单系统查询，这里返回一个示例结构
    # 随机决定是否有问题
    has_issue = random.choice([True, False, False])
    if not has_issue:
        return {
            "has_issue": False,
            "issue_type": None,
            "location": None,
            "tower_id": None,
            "tower_status": "normal",
            "fault_reason": None,
            "repair_eta": None,
            "affected_users": 0,
            "compensation": None,
        }

    return {
        "has_issue": True,
        "issue_type": "基站故障",
        "location": "广东省深圳市南山区（示例位置）",
        "tower_id": "BS1024",
        "tower_status": "fault",
        "fault_reason": "电力故障",
        "repair_eta": "30分钟",
        "affected_users": 234,
        "compensation": "2GB流量",
    }


async def handle_billing_dispute(user_id: str, message: str) -> dict:
    """
    处理扣费争议（示例实现）。
    真实逻辑应查询账单明细，这里重点是返回结构。
    """
    try:
        int(user_id)
    except ValueError:
        return {"has_error": False, "error_type": None}

    # 简单规则：如果用户提到“重复扣费/扣了两次”等关键字，判为 double_charge
    lower = message.lower()
    if "重复" in message or "扣了两次" in message or "double" in lower:
        error_type = "double_charge"
    elif "乱扣" in message or "不认识" in message or "unauthorized" in lower:
        error_type = "unauthorized"
    elif "资费" in message or "收费标准" in message or "rate" in lower:
        error_type = "rate_error"
    else:
        # 未识别为明显错误
        return {
            "has_error": False,
            "error_type": None,
            "description": "暂未识别出明显扣费异常，如仍有疑问建议人工客服核实账单。",
        }

    amount = 30.0
    date_str = (datetime.now() - timedelta(days=1)).date().isoformat()
    description = "流量叠加包重复扣费" if error_type == "double_charge" else "扣费存在疑问"

    auto_refund = True
    refund_amount = amount
    compensation = "赠送1GB流量"

    return {
        "has_error": True,
        "error_type": error_type,
        "amount": amount,
        "date": date_str,
        "description": description,
        "auto_refund": auto_refund,
        "refund_amount": refund_amount,
        "compensation": compensation,
    }


async def create_complaint_ticket(user_id: str, complaint: dict) -> dict:
    """
    创建投诉工单。
    complaint 可包含已识别的 type/sub_type 等元数据。
    """
    db = SessionLocal()
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"ticket_no": None, "status": "rejected", "message": "用户编号格式错误。"}

    try:
        user = db.get(User, user_id_int)
        if not user:
            return {
                "ticket_no": None,
                "status": "rejected",
                "message": "未找到该用户信息。",
            }

        title = complaint.get("title") or "用户投诉"
        content = complaint.get("content") or ""

        record = Complaint(
            user_id=user_id_int,
            title=title,
            content=content,
            status="processing",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        ticket_no = f"TKT{record.id:08d}"
        estimated_response = "30分钟内"
        contact_method = "短信通知"
        human_service = True

        return {
            "ticket_no": ticket_no,
            "status": record.status,
            "estimated_response": estimated_response,
            "contact_method": contact_method,
            "human_service": human_service,
        }
    finally:
        db.close()


async def get_complaint_status(ticket_no: str) -> dict:
    """
    查询投诉处理进度。
    当前示例通过解析 ticket_no 中的 ID 部分。
    """
    if not ticket_no.startswith("TKT"):
        return {"found": False, "reason": "invalid_ticket_no"}

    try:
        complaint_id = int(ticket_no.replace("TKT", ""))
    except ValueError:
        return {"found": False, "reason": "invalid_ticket_no"}

    db = SessionLocal()
    try:
        record = db.get(Complaint, complaint_id)
        if not record:
            return {"found": False, "reason": "not_found"}

        # 根据状态给出简单说明
        status = record.status
        if status == "open":
            desc = "工单已创建，等待客服受理。"
        elif status == "processing":
            desc = "工单处理中，工程师正在排查问题。"
        elif status == "closed":
            desc = "工单已处理完成，如仍有疑问可继续发起新投诉。"
        else:
            desc = "工单状态：{}".format(status)

        return {
            "found": True,
            "ticket_no": ticket_no,
            "status": status,
            "description": desc,
        }
    finally:
        db.close()


async def auto_compensate(user_id: str, issue_type: str) -> dict:
    """
    根据问题类型自动补偿（示例规则）：
    - 基站故障：2GB流量
    - 小额误扣（<50元）：自动退款+1GB
    - 大额误扣（>=50元）：退款+转人工
    - 权益问题：补发或积分
    """
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"success": False, "reason": "invalid_user_id"}

    db = SessionLocal()
    try:
        user = db.get(User, user_id_int)
        if not user:
            return {"success": False, "reason": "user_not_found"}

        # 用户价值可以决定补偿力度（示例）
        estimated_year_value = user_service.get_user_value(db, user_id_int)
        base_comp = "1GB流量"

        if issue_type == "network_outage":
            return {
                "success": True,
                "compensation_type": "data",
                "detail": "2GB流量",
                "message": "因基站故障给你带来的不便，我们已为你准备 2GB 流量补偿。",
            }

        if issue_type == "small_overcharge":
            return {
                "success": True,
                "compensation_type": "refund_and_data",
                "detail": "小额退款 + 1GB 流量",
                "message": "已为你发起小额退款，并额外赠送 1GB 流量作为补偿。",
            }

        if issue_type == "large_overcharge":
            return {
                "success": True,
                "compensation_type": "refund_and_human",
                "detail": "退款 + 人工跟进",
                "message": "已为你发起退款申请，同时安排人工客服专席跟进后续处理。",
            }

        if issue_type == "benefit_issue":
            if estimated_year_value >= 2000:
                detail = "权益补发 + 200 积分"
            else:
                detail = "权益补发"
            return {
                "success": True,
                "compensation_type": "benefit",
                "detail": detail,
                "message": "我们会为你补发相关权益，如有积分活动也会一并赠送。",
            }

        # 默认情况：根据用户价值赠送少量流量
        extra = "2GB" if estimated_year_value >= 1500 else "1GB"
        return {
            "success": True,
            "compensation_type": "data",
            "detail": f"{extra}流量",
            "message": f"已为你安排 {extra} 流量补偿，如仍有疑问可以随时联系人工客服。",
        }
    finally:
        db.close()

