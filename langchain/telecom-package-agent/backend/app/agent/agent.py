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

    async def chat(self, message: str) -> Dict[str, Any]:
        """处理用户消息的主逻辑。"""
        # 先尝试识别是否是明确的套餐相关意图，如果是则直接调用对应函数，避免绕远路。
        intent = await self._detect_package_intent(message)
        intent_type = intent.get("type", "other")

        if intent_type in {"query_current", "query_available", "need_recommend"}:
            output_text = await self.handle_package_query(message, intent)
            self.memory.add_message("human", message)
            self.memory.add_message("ai", output_text)
            need_human = self._check_human_intervention(output_text)
            suggestions = self._generate_suggestions(output_text)
            return {
                "response": output_text,
                "need_human": need_human,
                "suggestions": suggestions,
            }

        # 否则走通用 Agent 流程
        user_profile = await self._get_user_profile()

        # 将用户画像拼接到输入中，便于模型理解上下文
        profile_text = json.dumps(user_profile, ensure_ascii=False)
        full_input = f"用户画像：{profile_text}\n\n用户问题：{message}"

        response = await self.agent.ainvoke({"input": full_input})
        output_text = str(response.get("output", ""))

        # 写入对话记忆
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
