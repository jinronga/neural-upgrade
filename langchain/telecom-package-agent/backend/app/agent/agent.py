from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import redis
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import AIMessage, BaseMessage, HumanMessage
from langchain.tools import BaseTool
from langchain.tools.render import format_tool_to_openai_function

from app.agent.memory.conversation_memory import ConversationMemory
from app.agent.prompts.system_prompt import get_system_prompt
from app.agent.tools import (
    CheckNetworkStatusTool,
    ClaimBenefitTool,
    GetPendingBenefitsTool,
    HandleComplaintTool,
    QueryUsageTool,
    RecommendPackageTool,
)
from app.agent.functions import (
    get_available_packages,
    get_current_package,
    recommend_package,
)
from app.agent.functions.usage_functions import (
    check_usage_threshold,
    get_realtime_usage,
    recommend_topup,
)
from app.agent.functions.benefit_functions import (
    get_pending_benefits,
    recommend_benefit_to_claim,
    claim_benefit as fn_claim_benefit,
    claim_all_benefits,
    compensate_expired_benefit,
)
from app.agent.functions.change_functions import (
    check_change_eligibility,
    calculate_change_cost,
    submit_change_request,
    get_change_history,
)
from app.agent.functions.complaint_functions import (
    classify_complaint,
    diagnose_network_issue,
    handle_billing_dispute,
    create_complaint_ticket,
    auto_compensate,
)
from app.agent.functions.reminder_functions import (
    check_package_expiry,
    calculate_renewal_offer,
)
from app.core.config import settings
from app.database import SessionLocal
from app.services import benefit_service, usage_service, user_service

SYSTEM_PROMPT = get_system_prompt()


class SessionConversationMemory:
    """面向单个会话的记忆封装，内部使用 Redis 存储。"""

    def __init__(self, session_id: str, history_limit: int = 10) -> None:
        self.session_id = session_id
        self.history_limit = history_limit
        client = redis.from_url(settings.REDIS_URL)
        self._backend = ConversationMemory(client)

    def add_message(self, role: str, content: str) -> None:
        self._backend.add_message(self.session_id, role=role, content=content)

    def get_chat_history(self) -> List[BaseMessage]:
        """以 LangChain Message 列表形式返回最近的对话历史。"""
        raw_messages = self._backend.get_recent_messages(
            self.session_id, limit=self.history_limit
        )
        history: List[BaseMessage] = []
        for msg in raw_messages:
            if msg.role in {"human", "user"}:
                history.append(HumanMessage(content=msg.content))
            else:
                history.append(AIMessage(content=msg.content))
        return history


class TelecomAgent:
    """电信套餐智能 Agent，整合所有工具与对话记忆。"""

    def __init__(self, user_id: str, session_id: str) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self.memory = SessionConversationMemory(session_id)
        self.tools = self._init_tools()
        self.agent = self._init_agent()

    def _init_tools(self) -> List[BaseTool]:
        """初始化所有工具。"""
        db_factory = SessionLocal
        return [
            QueryUsageTool(db_session_factory=db_factory),
            RecommendPackageTool(db_session_factory=db_factory),
            GetPendingBenefitsTool(db_session_factory=db_factory),
            ClaimBenefitTool(db_session_factory=db_factory),
            HandleComplaintTool(db_session_factory=db_factory),
            CheckNetworkStatusTool(),
        ]

    def _init_agent(self) -> AgentExecutor:
        """初始化 LangChain Agent。"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        llm_with_tools = llm.bind(
            functions=[format_tool_to_openai_function(t) for t in self.tools]
        )

        agent_chain = {
            "input": lambda x: x["input"],
            "chat_history": lambda x: self.memory.get_chat_history(),
            "agent_scratchpad": lambda x: format_to_openai_function_messages(
                x["intermediate_steps"]
            ),
        } | prompt | llm_with_tools

        return AgentExecutor(agent=agent_chain, tools=self.tools, verbose=True)

    async def handle_package_query(self, message: str, intent: Dict[str, Any]) -> str:
        """处理套餐相关查询（供上层根据意图调用）。"""
        intent_type = intent.get("type", "other")

        if intent_type == "query_current":
            package = await get_current_package(self.user_id)
            if not package:
                return "暂未查询到你的当前套餐信息，可能当前没有激活的套餐，或需要稍后再试。"

            name = package.get("name", "未知套餐")
            price = package.get("price", 0.0)
            data_gb = package.get("data_gb", 0)
            voice_minutes = package.get("voice_minutes") or "若干"
            sms_count = package.get("sms_count") or "若干"

            return (
                f"您当前使用的是「{name}」套餐，月费约 ¥{price:.0f}，"
                f"包含约 {data_gb}GB 流量、{voice_minutes} 分钟语音、{sms_count} 条短信。"
            )

        if intent_type == "query_available":
            packages = await get_available_packages(self.user_id)
            return self.format_package_list(packages)

        if intent_type == "need_recommend":
            recommendation = await recommend_package(self.user_id)
            if not recommendation or "recommended" not in recommendation:
                return "暂时无法给出明确的套餐推荐，建议你先查看当前套餐详情，或稍后再试。"

            rec = recommendation["recommended"]
            name = rec.get("name", "某套餐")
            reason = rec.get("reason", "")
            return f"根据你的近期待机与用量情况，我推荐「{name}」。{reason}"

        return ""

    async def _detect_package_intent(self, message: str) -> Dict[str, Any]:
        """识别套餐相关意图，返回结构化 JSON。"""
        prompt = f"""
你是一个意图识别助手，专门识别与手机套餐相关的问题。
用户消息：{message}

请只返回一个 JSON 对象（不要额外解释或添加文字），格式如下：
{{
  "type": "query_current" | "query_available" | "need_recommend" | "query_detail" | "compare" | "other",
  "package_id": "如果用户明确提到了具体套餐ID或名称，否则留空字符串",
  "keywords": ["从用户话语中提取与套餐相关的关键词"],
  "target_group": "student|business|elder|general|'' （如能从语义中判断用户人群）"
}}
"""
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.0,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        try:
            resp = await llm.ainvoke(prompt)
            text = str(resp.content).strip()
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {"type": "other", "package_id": "", "keywords": [], "target_group": ""}

    def format_package_list(self, packages: List[Dict[str, Any]]) -> str:
        """将套餐列表格式化为适合口头说明的文本。"""
        if not packages:
            return "当前没有可供办理的套餐，或系统暂时无法获取套餐列表。"

        lines = ["我为你整理了几个可选套餐："]
        for idx, p in enumerate(packages[:5], start=1):
            name = p.get("name", "未知套餐")
            price = float(p.get("price", 0.0))
            data_gb = p.get("data_gb", 0)
            status = p.get("status", "active")
            status_text = "在售" if status == "active" else "暂不可办理"
            lines.append(
                f"{idx}. {name}：月费约 ¥{price:.0f}，包含约 {data_gb}GB 流量（当前状态：{status_text}）。"
            )

        if len(packages) > 5:
            lines.append("如需了解更多套餐详情，可以告诉我你更关注价格还是流量。")

        return "\n".join(lines)

    async def handle_usage_query(self, message: str, intent: Dict[str, Any]) -> str:
        """处理用量相关查询。"""
        intent_type = intent.get("type")

        if intent_type in {"query_usage", "query_remain"}:
            usage = await get_realtime_usage(self.user_id)
            if not usage:
                return "暂时无法查询到你的用量信息，请稍后再试。"

            user_profile = await self._get_user_profile()
            age_group = user_profile.get("age_group")

            data = usage.get("data", {})
            used = data.get("used", 0)
            remaining = data.get("remaining", 0)
            days_remaining = usage.get("days_remaining", 0)
            daily_avg = usage.get("daily_avg", 0)
            estimated_end = usage.get("estimated_end", "")

            if age_group == "elder":
                return (
                    f"您本月一共用了大约 {used:.1f}GB 流量，还剩 {remaining:.1f}GB。"
                    f"距离月底还有 {days_remaining} 天，正常使用是够用的，如果有异常情况可以随时告诉我。"
                )
            if age_group in {"18-25", "26-35"}:
                return (
                    f"📱 本月已用 {used:.1f}GB，剩余 {remaining:.1f}GB。"
                    f"按你最近每天大约 {daily_avg:.2f}GB 的节奏，大概会在 {estimated_end} 左右用完，注意合理安排哦~"
                )

            return (
                f"您好，您本月流量已使用约 {used:.1f}GB，剩余约 {remaining:.1f}GB，"
                f"账单周期还剩 {days_remaining} 天。"
            )

        if intent_type == "usage_warning":
            warning = await check_usage_threshold(self.user_id)
            if warning.get("has_warning"):
                w0 = warning.get("warnings", [{}])[0]
                suggestion = w0.get(
                    "suggestion", "建议适当控制近期用量，避免超出套餐。"
                )
                return f"⚠️ 温馨提示：{suggestion}"
            return "当前你的用量处于正常范围内，不用担心流量或语音会突然用完。"

        if intent_type == "buy_topup":
            need_gb = intent.get("need_gb") or 5.0
            try:
                need_gb_val = float(need_gb)
            except (TypeError, ValueError):
                need_gb_val = 5.0

            topup = await recommend_topup(self.user_id, need_gb_val)
            rec = topup.get("recommended", {})
            name = rec.get("name", "加油包")
            price = rec.get("price", 0.0)
            return (
                f"我推荐你办理「{name}」，价格约 ¥{price:.0f}，"
                "是否需要我继续为你模拟办理流程？"
            )

        return ""

    async def _match_benefit(self, benefit_name: str) -> Dict[str, Any] | None:
        """在待领权益中按名称模糊匹配一个权益。"""
        if not benefit_name:
            return None
        benefits = await get_pending_benefits(self.user_id)
        benefit_name_lower = benefit_name.lower()

        for b in benefits:
            if b["name"] == benefit_name:
                return b

        for b in benefits:
            if benefit_name_lower in b["name"].lower():
                return b

        return None

    async def handle_benefit_query(self, message: str, intent: Dict[str, Any]) -> str:
        """处理权益相关查询。"""
        intent_type = intent.get("type")

        if intent_type == "query_pending":
            benefits = await get_pending_benefits(self.user_id)

            if not benefits:
                return "您本月所有权益都已领取，下个月1号会发放新权益哦~"

            urgent = [b for b in benefits if b.get("is_urgent")]
            normal = [b for b in benefits if not b.get("is_urgent")]

            lines: list[str] = []
            if urgent:
                lines.append(f"⚠️ 您有{len(urgent)}个权益即将过期：")
                for b in urgent:
                    lines.append(
                        f"  {b.get('icon', '🎁')} {b['name']}（剩余{b.get('days_left', 0)}天）"
                    )

            if normal:
                lines.append("")
                lines.append("📦 其他待领权益：")
                for b in normal[:3]:
                    lines.append(f"  {b.get('icon', '🎁')} {b['name']}")

            rec = await recommend_benefit_to_claim(self.user_id)
            if rec:
                lines.append("")
                lines.append(f"💡 建议先领{rec['name']}，{rec['reason']}")

            return "\n".join(lines)

        if intent_type == "claim":
            benefit_name = intent.get("benefit_name")
            benefit = await self._match_benefit(benefit_name)

            if not benefit:
                return f"没找到“{benefit_name}”，您可以回复“我的权益”查看可领取的权益。"

            result = await fn_claim_benefit(self.user_id, benefit["benefit_id"], "agent")
            if not result.get("success"):
                return f"❌ 领取失败，{result.get('message', '请稍后重试')}"

            delivery_type = result.get("delivery_type")
            if delivery_type == "api_direct":
                return f"✅ {benefit['name']}已领取成功，{result.get('message', '')}"
            if delivery_type == "card_password":
                return (
                    f"✅ {benefit['name']}已领取，卡号：{result.get('card_no')}，"
                    f"密码：{result.get('password')}，请复制后到 App 兑换。"
                )
            return f"✅ {benefit['name']}已领取成功，可在权益中心查看详情。"

        if intent_type == "claim_all":
            result = await claim_all_benefits(self.user_id)
            return (
                f"✅ 已为您领取{result['success_count']}个权益，"
                f"部分失败数量：{result['failed_count']}。"
            )

        if intent_type == "expired_complaint":
            benefit_name = intent.get("benefit_name")
            benefit = await self._match_benefit(benefit_name)
            if not benefit:
                return f"很抱歉，没找到与“{benefit_name}”匹配的权益记录。"

            compensation = await compensate_expired_benefit(
                self.user_id, benefit["benefit_id"]
            )
            if compensation.get("can_compensate"):
                method = compensation.get("method")
                if method == "free":
                    return "已为您免费补发该权益，请稍后在权益中心查看。"
                if method == "points":
                    return (
                        f"可以扣除 {compensation['points_needed']} 积分补发，"
                        f"您当前有 {compensation['user_points']} 积分，需要我为你发起补发吗？"
                    )
            return "很抱歉，该权益已超过补领期限，如有特殊情况建议联系人工客服。"

        return ""

    async def handle_change_query(self, message: str, intent: Dict[str, Any]) -> str:
        """处理套餐变更相关查询。"""
        intent_type = intent.get("type")

        if intent_type == "want_change":
            target_package = intent.get("target_package")
            if not target_package:
                return "请告诉我你想变更到哪个套餐。"

            current = await get_current_package(self.user_id)
            eligible = await check_change_eligibility(self.user_id, target_package)
            if not eligible.get("eligible"):
                return f"抱歉，您暂时无法变更套餐：{eligible.get('reason', '不满足变更条件')}"

            cost = await calculate_change_cost(self.user_id, target_package)
            if not cost:
                return "暂时无法计算变更费用，请稍后再试或联系人工客服。"

            lines: list[str] = []
            lines.append(f"您当前套餐：{current['name']}（{current['price']}元/月）")
            lines.append(
                f"目标套餐：{cost['to_package']['name']}（{cost['to_package']['price']}元/月）"
            )
            lines.append("")

            if cost["change_type"] == "upgrade":
                lines.append("📈 升级套餐")
                lines.append(
                    f"• 剩余流量：{cost['data_carryover']['original']}GB → "
                    f"结转 {cost['data_carryover']['carryover']}GB"
                )
                lines.append(
                    f"• 剩余语音：{cost['voice_carryover']['original']}分钟 → "
                    f"结转 {cost['voice_carryover']['carryover']}分钟"
                )
                lines.append(
                    f"• 本月差价：{cost['price_diff']['pro_rated']}元（按剩余天数折算）"
                )
                lines.append(
                    f"• 未领权益：将折 {cost['benefit_changes']['pending_disposition']}"
                )
                lines.append("")
                lines.append(
                    "升级后您将获得："
                    + ", ".join(cost["benefit_changes"]["new_benefits"])
                )
                lines.append(
                    f"\n需要支付{cost['price_diff']['total_to_pay']}元，立即生效。确认变更吗？"
                )

            elif cost["change_type"] == "downgrade":
                lines.append("📉 降级套餐")
                lines.append("⚠️ 降级将在次月1日生效")
                lines.append(
                    f"• 本月已领权益："
                    f"{', '.join(cost['benefit_changes']['current_month_claimed'])}（保留）"
                )
                lines.append(
                    f"• 本月未领权益："
                    f"{', '.join(cost['benefit_changes']['current_month_pending'])}（需本月领取）"
                )
                lines.append(
                    "\n确认要降级吗？降级后无法恢复本月的高档权益。"
                )

            return "\n".join(lines)

        if intent_type == "confirm_change":
            target_package = intent.get("target_package")
            if not target_package:
                return "请先告诉我你想变更到哪个套餐，然后再确认。"

            result = await submit_change_request(
                self.user_id, target_package, confirm=True
            )
            if not result.get("success"):
                return f"变更失败：{result.get('message', '请稍后重试')}"

            if result.get("payment_required"):
                return (
                    f"变更申请已提交，请支付 {result['payment_amount']} 元，"
                    "支付链接已通过短信发送至你的手机。"
                )
            return f"变更成功，新套餐将于 {result['effective_date']} 生效。"

        if intent_type == "change_history":
            history = await get_change_history(self.user_id)
            if not history:
                return "您暂无套餐变更记录。"

            lines = ["📋 最近变更记录："]
            for h in history[:3]:
                lines.append(
                    f"• {h['change_date']}：{h['from_package']} → {h['to_package']}（{h['status']}）"
                )
            return "\n".join(lines)

        return ""

    async def transfer_to_human(self, reason: str) -> None:
        """
        简单的转人工占位实现：这里只是记录原因。
        真实环境可在此处写入一个“转人工”工单或通知客服系统。
        """
        _ = reason
        return None

    async def handle_benefit_complaint(self, message: str) -> str:
        """
        处理与权益相关的投诉（示例：尝试补发过期权益）。
        """
        return (
            "已记录你的权益问题，如果是近期刚过期的权益，我可以尝试为你申请补发，"
            "你也可以先在“权益中心”查看本月可领取的权益。"
        )

    async def handle_complaint(self, message: str) -> str:
        """处理用户投诉。"""
        complaint = await classify_complaint(message)

        if complaint["sentiment"] == "angry" or complaint["urgency"] == "high":
            await self.transfer_to_human(
                reason=f"用户情绪{complaint['sentiment']}，投诉类型：{complaint['type']}"
            )
            return "你的问题比较紧急，正在为你转接人工客服，请稍候…"

        if complaint["type"] == "network_slow":
            network = await diagnose_network_issue(self.user_id)
            if network.get("has_issue"):
                compensation = await auto_compensate(self.user_id, "network_outage")
                detail = compensation.get("detail", "一定的流量补偿")
                return (
                    f"检测到你附近基站正在抢修，预计 {network.get('repair_eta', '稍后')} 恢复。"
                    f"我们已为你安排 {detail}，抱歉给你带来不便。"
                )
            return (
                "当前网络整体运行正常，你所在位置可能属于室内弱覆盖区域。\n"
                "建议尝试：\n1）靠近窗户\n2）重启手机\n3）关闭 5G 切换到 4G。\n"
                "如果问题持续，我可以为你创建网络优化工单。"
            )

        if complaint["type"] == "overcharge":
            dispute = await handle_billing_dispute(self.user_id, message)
            if dispute.get("has_error") and dispute.get("auto_refund"):
                return (
                    f"已核实存在 {dispute['description']}，已为你自动退还 "
                    f"{dispute['refund_amount']} 元，并赠送 {dispute['compensation']}。请查收短信。"
                )
            ticket = await create_complaint_ticket(self.user_id, complaint)
            return (
                f"已为你创建扣费核实工单 {ticket['ticket_no']}，"
                f"客服将在 {ticket['estimated_response']} 内与你联系。"
            )

        if complaint["type"] == "benefit_missing":
            return await self.handle_benefit_complaint(message)

        ticket = await create_complaint_ticket(self.user_id, complaint)
        return (
            f"已记录你的问题，工单号：{ticket['ticket_no']}，"
            "我们会尽快处理并通过短信或 App 通知你结果。"
        )

    async def handle_reminder_query(self, message: str, intent: Dict[str, Any]) -> str:
        """处理续费相关查询。"""
        intent_type = intent.get("type")

        if intent_type == "check_expiry":
            expiry = await check_package_expiry(self.user_id)
            if not expiry.get("expire_date"):
                return "目前没有检测到在用套餐，如有需要可以让我帮你选择一个合适的套餐。"

            if expiry["expiring_soon"]:
                lines = [
                    f"你的套餐将在 {expiry['days_left']} 天后到期（{expiry['expire_date']}）。"
                ]
                if expiry["auto_renew"]:
                    lines.append(
                        f"自动续费已开启，到期后将自动扣费 ¥{expiry['renew_amount']:.0f} 续费一个月。"
                    )
                    offer = await calculate_renewal_offer(self.user_id)
                    if offer.get("has_offer"):
                        lines.append(
                            f"🎁 同时你有续费优惠：{offer['description']}，预计可节省约 ¥{offer['saving']:.0f}。"
                        )
                else:
                    lines.append(
                        "当前未开启自动续费，到期后套餐将暂停，建议你提前续费或选择新的套餐。"
                    )
                return "\n".join(lines)

            return (
                f"你的套餐有效期到 {expiry['expire_date']}，"
                "距离到期还有一段时间，可以放心使用。"
            )

        if intent_type == "renewal_offer":
            offer = await calculate_renewal_offer(self.user_id)
            if offer.get("has_offer"):
                return (
                    f"你当前可享受续费优惠：{offer['description']}，"
                    f"预计可为你节省约 ¥{offer['saving']:.0f}。"
                )
            return "当前暂无专属续费优惠活动，后续如有新的活动会通过短信或 App 通知你。"

        return ""

    async def _get_user_profile(self) -> Dict[str, Any]:
        """获取用户画像信息，用于给 LLM 作为上下文。"""

        def _inner() -> Dict[str, Any]:
            try:
                user_id_int = int(self.user_id)
            except ValueError:
                return {"user_id": self.user_id, "valid": False}

            db = SessionLocal()
            try:
                user = user_service.get_user_by_id(db, user_id_int)
                if not user:
                    return {"user_id": user_id_int, "valid": False}

                estimated_value = user_service.get_user_value(db, user_id_int)
                current_usage_mb = usage_service.get_current_usage(
                    db, user_id_int, redis_client=None
                )
                pending_benefits = benefit_service.get_pending_benefits(
                    db, user_id_int
                )

                return {
                    "user_id": user_id_int,
                    "valid": True,
                    "name": user.name,
                    "phone_number": user.phone_number,
                    "status": user.status,
                    "estimated_year_value": estimated_value,
                    "current_usage_mb": current_usage_mb,
                    "pending_benefits": [b.name for b in pending_benefits],
                }
            finally:
                db.close()

        return await asyncio.to_thread(_inner)

    def _check_human_intervention(self, model_output: str) -> bool:
        """根据回复内容简单判断是否建议转人工。"""
        text = model_output or ""
        keywords = ["转人工", "人工客服", "无法处理", "无法解决", "请致电客服"]
        return any(k in text for k in keywords)

    def _generate_suggestions(self, model_output: str) -> List[str]:
        """根据当前回复生成一些后续建议。"""
        suggestions: List[str] = [
            "如问题较为复杂或紧急，你可以直接回复“转人工客服”，由人工专席继续为你处理。",
            "如果对当前套餐不满意，可以让我根据你的使用情况重新推荐更合适的套餐。",
        ]
        if "网络" in (model_output or ""):
            suggestions.append("如果网络问题持续存在，建议在信号较好的位置再次测试，或尝试重启设备。")
        return suggestions

    async def _detect_global_intent(self, message: str) -> Dict[str, Any]:
        """
        使用 LLM 一次性识别全局意图：
        - domain: package/usage/benefit/change/complaint/reminder/other
        - intent: 细分类型及槽位，供对应的 handle_* 方法使用
        """
        prompt = f"""
你是一个意图识别助手，负责将用户的一句话路由到合适的业务域。

用户消息：
{message}

请只返回一个 JSON 对象（不要多余说明），格式如下：
{{
  "domain": "package" | "usage" | "benefit" | "change" | "complaint" | "reminder" | "other",
  "intent": {{
    "type": "..."
    // 下面字段按需填充即可，可以缺省
    "target_package": "当用户提到想办/换的具体套餐或档位，尽量抽取标准名称或ID",
    "benefit_name": "当用户提到具体权益名称，如腾讯视频、咖啡券等",
    "need_gb": 5.0
  }}
}}

各域常见意图举例（type 字段）：
- package 域：
  - "query_current"：想问当前套餐是什么
  - "query_available"：想了解有哪些套餐可选
  - "need_recommend"：让你推荐套餐
  - "query_detail"：想看某个套餐的详细说明
  - "compare"：对比两个或多个套餐
- usage 域：
  - "query_usage"："我用了多少流量" 之类
  - "query_remain"："还剩多少流量"
  - "usage_warning"："会不会超"、"快不快用完"
  - "buy_topup"："买加油包"、"再加点流量"
- benefit 域：
  - "query_pending"："我的权益"、"有什么券没领"
  - "claim"："帮我领腾讯会员" 等，benefit_name 应填权益名字
  - "claim_all"："一键领取"
  - "expired_complaint"："权益过期了怎么办"
- change 域：
  - "want_change"："我要把29档换成49档" 等
  - "confirm_change"：在你给出变更方案后确认办理
  - "change_history"："看下我之前改套餐记录"
- complaint 域：
  - 不需要很细分 type，可以简单用 "generic" 或 "network_slow"/"overcharge"/"benefit_missing" 等
- reminder 域：
  - "check_expiry"："套餐啥时候到期"、"快到期了吗"
  - "renewal_offer"："有没有续费优惠"

请务必输出合法 JSON，确保 domain 与 intent.type 与上述约定对齐。
"""

        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.0,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        try:
            resp = await llm.ainvoke(prompt)
            text = str(resp.content).strip()
            data = json.loads(text)
            if isinstance(data, dict):
                # 兜底结构
                domain = data.get("domain") or "other"
                intent = data.get("intent") or {}
                if not isinstance(intent, dict):
                    intent = {}
                return {"domain": domain, "intent": intent}
        except Exception:
            pass

        return {"domain": "other", "intent": {}}

    async def chat(self, message: str) -> Dict[str, Any]:
        """处理用户消息的主逻辑。"""
        # 1. 全局意图识别
        intent_info = await self._detect_global_intent(message)
        domain = intent_info.get("domain", "other")
        intent = intent_info.get("intent", {}) or {}

        # 2. 根据 domain 分发到对应处理函数
        output_text: str | None = None

        if domain == "package":
            output_text = await self.handle_package_query(message, intent)
        elif domain == "usage":
            output_text = await self.handle_usage_query(message, intent)
        elif domain == "benefit":
            output_text = await self.handle_benefit_query(message, intent)
        elif domain == "change":
            output_text = await self.handle_change_query(message, intent)
        elif domain == "complaint":
            output_text = await self.handle_complaint(message)
        elif domain == "reminder":
            output_text = await self.handle_reminder_query(message, intent)

        # 3. 如果某个专用 handler 已经给出回复，则直接返回（绕过通用 Agent）
        if output_text:
            self.memory.add_message("human", message)
            self.memory.add_message("ai", output_text)
            need_human = self._check_human_intervention(output_text)
            suggestions = self._generate_suggestions(output_text)
            return {
                "response": output_text,
                "need_human": need_human,
                "suggestions": suggestions,
            }

        # 4. 否则走通用 Agent 流程（工具 + LLM）
        user_profile = await self._get_user_profile()
        profile_text = json.dumps(user_profile, ensure_ascii=False)
        full_input = f"用户画像：{profile_text}\n\n用户问题：{message}"

        response = await self.agent.ainvoke({"input": full_input})
        output_text = str(response.get("output", ""))

        self.memory.add_message("human", message)
        self.memory.add_message("ai", output_text)

        need_human = self._check_human_intervention(output_text)
        suggestions = self._generate_suggestions(output_text)

        return {
            "response": output_text,
            "need_human": need_human,
            "suggestions": suggestions,
        }


async def chat_with_agent(user_id: str, session_id: str, message: str) -> Dict[str, Any]:
    """便捷函数：创建一个 TelecomAgent 实例并处理一次对话。"""
    agent = TelecomAgent(user_id=user_id, session_id=session_id)
    return await agent.chat(message)
