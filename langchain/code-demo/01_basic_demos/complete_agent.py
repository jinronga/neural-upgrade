# complete_agent.py - 整合所有功能的完整智能体
from __future__ import annotations

import os
from typing import TypedDict, List, Annotated, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from challenge_memory import MemoryManager
from challenge_multi_tool import build_multi_tool_graph, MultiToolState
from challenge_math_expert import MathExpertAgent


class CompleteAgentState(TypedDict):
    """完整智能体的统一状态结构"""

    # 对话历史（人类 + AI 消息）
    messages: Annotated[List, add_messages]

    # 记忆相关
    conversation_id: str
    user_id: str
    memory_context: str

    # 路由控制
    route: Literal[
        "router",
        "multi_tool",
        "math_expert",
        "direct_answer",
        "error",
        "__end__",
    ]


# ========= 1. 初始化 LLM =========
ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
    temperature=0.1,
)


# ========= 2. 记忆节点 =========
def memory_node(state: CompleteAgentState) -> CompleteAgentState:
    """记忆节点：加载 / 更新对话记忆，并写入 memory_context"""
    print("\n[记忆节点] 处理对话记忆...")

    memory_manager = MemoryManager()
    conversation_id = state.get("conversation_id", "default_conv")
    user_id = state.get("user_id", "default")

    # 获取或创建记忆
    memory = memory_manager.get_memory(conversation_id, user_id)

    # 提取与当前问题相关的上下文
    current_query = (
        state["messages"][-1].content if state.get("messages") else ""
    )
    memory_context = memory_manager.extract_memory_context(
        conversation_id, current_query
    )
    state["memory_context"] = memory_context

    # 简单的实体 / 偏好更新示例（可按需扩展）
    entities = {}
    if "时间" in current_query:
        entities["时间查询"] = "用户询问时间相关"
    if "计算" in current_query or "等于" in current_query:
        entities["计算需求"] = "用户需要数学计算"

    memory.update(
        {
            "entities": entities,
            "preferences": ["需要详细计算"] if "计算" in current_query else [],
        }
    )
    memory_manager.save_memories()

    # 记忆处理完毕，进入路由节点
    state["route"] = "router"
    return state


# ========= 3. 路由节点 =========
router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一个路由助手，负责为完整智能体选择合适的处理模块。

可用模块：
- "multi_tool"：适用于需要多步工具计算或外部能力的问题，例如：
  - 单位换算 + 数学计算
  - 货币换算 + 加总
  - 组合使用时间、计算器、单位转换等工具
  - 需要进行实时信息搜索或读取项目内文件内容的问题
- "math_expert"：适用于中等及以上难度的数学题，例如：
  - 解方程、几何计算、微积分、数列等
  - 需要严格数学推导和详细步骤的题目
- "direct_answer"：适用于普通对话或简单问答，不需要复杂计算或工具。

请根据用户最近一条消息，选择最合适的模块，并返回 JSON：
{{
  "route": "multi_tool" | "math_expert" | "direct_answer",
  "reason": "选择原因"
}}
""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


def router_node(state: CompleteAgentState) -> CompleteAgentState:
    """路由节点：决定使用 多工具 / 数学专家 / 直接回答"""
    print("\n[路由节点] 分析问题，决定处理模块...")

    messages = state["messages"]
    try:
        response = llm.invoke(
            router_prompt.format_messages(messages=messages)
        )
        content = response.content.strip()

        # 优先尝试解析 JSON
        import json

        decision = None
        if content.startswith("{") and content.endswith("}"):
            decision = json.loads(content)

        if decision is None:
            # 简单回退：按关键词启发式路由
            last = messages[-1].content if messages else ""
            route = "direct_answer"
            if any(k in last for k in ["积分", "导数", "微积分", "极限"]):
                route = "math_expert"
            elif any(
                k in last
                for k in [
                    "单位",
                    "换算",
                    "公里",
                    "厘米",
                    "美元",
                    "人民币",
                    "欧元",
                    "搜索",
                    "查一下",
                    "最新",
                    "打开文件",
                    "读取文件",
                ]
            ):
                route = "multi_tool"
            state["route"] = route
            print(f"[路由节点] 启发式决策: {route}")
            return state

        route = decision.get("route", "direct_answer")
        print(f"[路由节点] LLM 决策 route = {route}，原因: {decision.get('reason')}")

        if route not in {"multi_tool", "math_expert", "direct_answer"}:
            route = "direct_answer"

        state["route"] = route
        return state

    except Exception as e:
        print(f"[路由节点] 决策失败，回退为 direct_answer: {e}")
        state["route"] = "direct_answer"
        return state


# ========= 4. 多工具节点 =========
def multi_tool_node(state: CompleteAgentState) -> CompleteAgentState:
    """多工具节点：调用 challenge_multi_tool 的工作流"""
    print("\n[多工具节点] 调用多工具工作流...")

    user_query = (
        state["messages"][-1].content if state.get("messages") else ""
    )

    # 构造 MultiToolState
    from langchain_core.messages import HumanMessage as HGHumanMessage

    initial_state = MultiToolState(
        messages=[HGHumanMessage(content=user_query)],
        tool_calls=[],
        pending_tools=[],
        current_step="开始",
        max_steps=10,
        step_count=0,
        next_node="planning",
    )

    graph = build_multi_tool_graph()
    final_state = graph.invoke(initial_state)

    # 取最后一条 AI 消息作为最终回答
    final_messages = final_state.get("messages", [])
    final_answer = (
        final_messages[-1].content if final_messages else "（多工具工作流未产生回答）"
    )

    state["messages"].append(AIMessage(content=final_answer))
    state["route"] = "__end__"
    return state


# ========= 5. 数学专家节点 =========
def math_expert_node(state: CompleteAgentState) -> CompleteAgentState:
    """数学专家节点：调用 MathExpertAgent"""
    print("\n[数学专家节点] 调用数学专家智能体...")

    user_query = (
        state["messages"][-1].content if state.get("messages") else ""
    )

    agent = MathExpertAgent()
    explanation = agent.solve_step_by_step(user_query)

    state["messages"].append(AIMessage(content=explanation))
    state["route"] = "__end__"
    return state


# ========= 6. 直接回答节点 =========
direct_answer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一个有记忆的友好 AI 助手。
下面是与该用户相关的历史记忆（如果有）：
{memory_context}

在回答当前问题时：
- 尽量利用上述记忆信息（如用户偏好、已提到的实体）
- 如果记忆为空，按普通助手回答即可
""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


def direct_answer_node(state: CompleteAgentState) -> CompleteAgentState:
    """直接回答节点：普通对话，不调用多工具或数学专家"""
    print("\n[直接回答节点] 使用通用 LLM 回答...")

    memory_context = state.get("memory_context", "")
    messages = state["messages"]

    response = llm.invoke(
        direct_answer_prompt.format_messages(
            memory_context=memory_context,
            messages=messages,
        )
    )

    state["messages"].append(AIMessage(content=response.content))
    state["route"] = "__end__"
    return state


# ========= 7. 错误处理节点 =========
def error_node(state: CompleteAgentState) -> CompleteAgentState:
    print("\n[错误节点] 处理异常...")
    state["messages"].append(
        AIMessage(
            content="抱歉，处理您的请求时发生了错误，请稍后再试或换一种问法。"
        )
    )
    state["route"] = "__end__"
    return state


# ========= 8. 构建完整智能体图 =========
def build_complete_agent():
    """构建包含记忆、多工具和数学专家的完整智能体工作流"""
    workflow = StateGraph(CompleteAgentState)

    # 注册节点
    workflow.add_node("memory", memory_node)
    workflow.add_node("router", router_node)
    workflow.add_node("multi_tool", multi_tool_node)
    workflow.add_node("math_expert", math_expert_node)
    workflow.add_node("direct_answer", direct_answer_node)
    workflow.add_node("error", error_node)

    # 入口：先走记忆节点
    workflow.set_entry_point("memory")

    # 记忆节点固定流向路由节点
    workflow.add_edge("memory", "router")

    # 路由节点根据 route 决定下一步
    def route_decision(state: CompleteAgentState) -> str:
        return state.get("route", "error")

    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "multi_tool": "multi_tool",
            "math_expert": "math_expert",
            "direct_answer": "direct_answer",
            "error": "error",
        },
    )

    # 非路由节点都直接结束
    workflow.add_edge("multi_tool", END)
    workflow.add_edge("math_expert", END)
    workflow.add_edge("direct_answer", END)
    workflow.add_edge("error", END)

    return workflow.compile()


# ========= 9. 运行入口函数 =========
def run_complete_agent(
    query: str,
    conversation_id: str = "default_conv",
    user_id: str = "default",
) -> str:
    """单次调用完整智能体，返回最终回答文本"""
    print("\n" + "=" * 60)
    print(f"完整智能体 - 用户问题: {query}")
    print("=" * 60)

    initial_state: CompleteAgentState = CompleteAgentState(
        messages=[HumanMessage(content=query)],
        conversation_id=conversation_id,
        user_id=user_id,
        memory_context="",
        route="router",
    )

    graph = build_complete_agent()
    final_state = graph.invoke(initial_state)

    msgs = final_state["messages"]
    # 返回最后一条 AI 消息
    for msg in reversed(msgs):
        if msg.type == "ai":
            return msg.content
    return "（未生成回答）"


if __name__ == "__main__":
    # 一些示例问题
    test_queries = [
        "现在的时间加上30分钟是多少？",
        "把5公里转换成米，再加上500厘米，一共是多少米？",
        "解方程：2x + 5 = 13",
        "一个圆的半径是7厘米，求它的面积和周长",
        "我们之前聊到我喜欢什么？",
    ]

    for i, q in enumerate(test_queries, 1):
        ans = run_complete_agent(q, conversation_id="demo_conv_001")
        print(f"\n[最终回答 {i}]\n{ans}")
        print("-" * 60)

