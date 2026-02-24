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
