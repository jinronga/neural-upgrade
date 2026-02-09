import os
from typing import TypedDict, List, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import math
import json

# ==================== 1. 定义扩展状态（State） ====================
class AdvancedAgentState(TypedDict):
    """扩展的工作流状态，包含更多信息用于多节点工作流"""
    messages: Annotated[List, add_messages]  # 对话消息历史
    selected_tool: str  # 选中的工具名称
    tool_input: str  # 工具输入
    tool_result: str  # 工具执行结果
    route: Literal["router", "execute_tool", "validate", "summarize", "error_handler", "__end__"]  # 当前路由

# ==================== 2. 定义所有工具 ====================
@tool
def calculator(expression: str) -> str:
    """执行数学计算。支持加减乘除、平方、开方等。
    示例: '2 + 3 * 4' 或 'sqrt(16)' 或 'pow(2, 3)'"""
    try:
        allowed_names = {
            'abs': abs, 'round': round, 'pow': pow, 
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'pi': math.pi, 'e': math.e
        }
        expression = expression.replace('^', '**').replace('×', '*').replace('÷', '/')
        result = eval(expression, {"__builtins__": {}}, {**allowed_names, 'math': math})
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

@tool
def get_current_time() -> str:
    """获取当前日期和时间。"""
    from datetime import datetime
    now = datetime.now()
    return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')}"

@tool
def web_search(query: str) -> str:
    """搜索网络获取最新信息。"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return "\n".join([f"{r['title']}: {r['body']}" for r in results])
            return "没有找到相关信息"
    except ImportError:
        return "搜索功能需要安装: pip install duckduckgo-search"
    except Exception as e:
        return f"搜索失败: {str(e)}"

@tool
def get_weather(city: str) -> str:
    """获取城市天气信息。"""
    weather_data = {
        "北京": "晴，15°C，空气质量良",
        "上海": "多云，18°C，空气质量优", 
        "广州": "阵雨，22°C，空气质量良",
        "深圳": "晴，24°C，空气质量优"
    }
    return weather_data.get(city, f"暂无{city}的天气信息")

# 所有工具
all_tools = [calculator, get_current_time, web_search, get_weather]
tools_dict = {t.name: t for t in all_tools}

# ==================== 3. 创建模型 ====================
ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
    temperature=0.1,
)

# ==================== 4. 工具描述函数 ====================
def render_text_description(tools):
    """将工具列表转换为文本描述"""
    descriptions = []
    for t in tools:
        desc = f"- {t.name}: {t.description}"
        descriptions.append(desc)
    return "\n".join(descriptions)

# ==================== 5. 创建各个节点（Node） ====================

# 节点1：路由节点 - 智能分析问题，决定使用哪个工具
router_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个智能路由助手，负责分析用户问题并决定使用哪个工具。

可用工具：
{tools}

分析用户问题，如果：
- 需要计算或数学运算 → 返回 calculator
- 询问时间 → 返回 get_current_time
- 需要最新信息或搜索 → 返回 web_search
- 询问天气 → 返回 get_weather
- 不需要工具，直接回答 → 返回 "none"

请严格按照以下JSON格式响应：
{{
    "tool": "工具名称或none",
    "tool_input": "工具输入（如果需要工具）"
}}"""),
    MessagesPlaceholder(variable_name="messages"),
])

def router_node(state: AdvancedAgentState):
    """路由节点：分析问题，决定使用哪个工具"""
    print("\n[路由节点] 正在分析问题...")
    
    tools_description = render_text_description(all_tools)
    messages = state["messages"]
    
    response = llm.invoke(router_prompt.format_messages(
        tools=tools_description,
        messages=messages
    ))
    
    try:
        content = response.content.strip()
        # 尝试解析JSON
        if content.startswith("{") and content.endswith("}"):
            decision = json.loads(content)
            tool_name = decision.get("tool", "none")
            tool_input = decision.get("tool_input", "")
            
            if tool_name == "none":
                print("[路由节点] 决定：不需要工具，直接回答")
                state["route"] = "summarize"
            elif tool_name in tools_dict:
                print(f"[路由节点] 决定：使用工具 {tool_name}，输入: {tool_input}")
                state["selected_tool"] = tool_name
                state["tool_input"] = tool_input
                state["route"] = "execute_tool"
            else:
                print(f"[路由节点] 未知工具: {tool_name}，转到错误处理")
                state["route"] = "error_handler"
        else:
            # 从文本中提取工具名称
            for tool_name in tools_dict.keys():
                if tool_name in content.lower():
                    state["selected_tool"] = tool_name
                    # 尝试提取输入
                    if "tool_input" in content.lower():
                        import re
                        match = re.search(r'tool_input["\']?\s*:\s*["\']?([^"\']+)', content, re.IGNORECASE)
                        if match:
                            state["tool_input"] = match.group(1).strip()
                    state["route"] = "execute_tool"
                    return state
            state["route"] = "summarize"
    except Exception as e:
        print(f"[路由节点] 解析错误: {e}，转到错误处理")
        state["route"] = "error_handler"
    
    return state

# 节点2：工具执行节点 - 执行选定的工具
def execute_tool_node(state: AdvancedAgentState):
    """工具执行节点：执行选定的工具"""
    print(f"\n[工具执行节点] 执行工具: {state['selected_tool']}")
    
    tool_name = state["selected_tool"]
    tool_input = state["tool_input"]
    
    try:
        if tool_name in tools_dict:
            result = tools_dict[tool_name].invoke(tool_input)
            state["tool_result"] = result
            print(f"[工具执行节点] 工具返回: {result[:100]}...")
            state["route"] = "validate"
        else:
            state["tool_result"] = f"未知工具: {tool_name}"
            state["route"] = "error_handler"
    except Exception as e:
        state["tool_result"] = f"工具执行失败: {str(e)}"
        state["route"] = "error_handler"
    
    return state

# 节点3：验证节点 - 验证工具结果是否合理
validate_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个验证助手，检查工具执行结果是否合理。

用户问题: {user_question}
工具名称: {tool_name}
工具输入: {tool_input}
工具结果: {tool_result}

请判断：
1. 结果是否合理？
2. 是否回答了用户的问题？
3. 是否需要重新执行工具？

返回JSON格式：
{{
    "valid": true/false,
    "reason": "验证原因",
    "need_retry": true/false
}}"""),
])

def validate_node(state: AdvancedAgentState):
    """验证节点：验证工具结果"""
    print("\n[验证节点] 正在验证工具结果...")
    
    # 获取用户原始问题
    user_question = state["messages"][0].content if state["messages"] else ""
    
    try:
        response = llm.invoke(validate_prompt.format_messages(
            user_question=user_question,
            tool_name=state["selected_tool"],
            tool_input=state["tool_input"],
            tool_result=state["tool_result"]
        ))
        
        validation = json.loads(response.content)
        is_valid = validation.get("valid", True)
        need_retry = validation.get("need_retry", False)
        
        print(f"[验证节点] 验证结果: {'通过' if is_valid else '未通过'}")
        
        if need_retry:
            print("[验证节点] 需要重试，返回工具执行节点")
            state["route"] = "execute_tool"
        elif is_valid:
            print("[验证节点] 验证通过，转到总结节点")
            state["route"] = "summarize"
        else:
            print("[验证节点] 验证失败，转到错误处理")
            state["route"] = "error_handler"
    except Exception as e:
        print(f"[验证节点] 验证过程出错: {e}，转到总结节点")
        state["route"] = "summarize"
    
    return state

# 节点4：总结节点 - 生成最终回答
summarize_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个总结助手，基于工具结果或直接回答用户问题。

用户问题: {user_question}
工具结果: {tool_result}

请生成一个清晰、准确的最终回答。如果使用了工具，要基于工具结果回答。"""),
])

def summarize_node(state: AdvancedAgentState):
    """总结节点：生成最终回答"""
    print("\n[总结节点] 正在生成最终回答...")
    
    user_question = state["messages"][0].content if state["messages"] else ""
    tool_result = state.get("tool_result", "")
    
    # 如果有工具结果，使用工具结果；否则直接回答
    if tool_result:
        response = llm.invoke(summarize_prompt.format_messages(
            user_question=user_question,
            tool_result=tool_result
        ))
    else:
        # 直接回答，不需要工具
        tools_description = render_text_description(all_tools)
        direct_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个有帮助的AI助手。直接回答用户问题，不需要使用工具。"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        response = llm.invoke(direct_prompt.format_messages(
            messages=state["messages"]
        ))
    
    # 添加最终回答到消息历史
    state["messages"].append(response)
    print(f"[总结节点] 生成最终回答: {response.content[:100]}...")
    state["route"] = "__end__"
    
    return state

# 节点5：错误处理节点 - 处理异常情况
def error_handler_node(state: AdvancedAgentState):
    """错误处理节点：处理异常情况"""
    print("\n[错误处理节点] 处理错误...")
    
    error_msg = state.get("tool_result", "未知错误")
    user_question = state["messages"][0].content if state["messages"] else ""
    
    # 生成错误提示
    error_response = f"抱歉，处理您的问题时遇到了问题：{error_msg}。请重新提问或尝试其他方式。"
    state["messages"].append(AIMessage(content=error_response))
    
    print(f"[错误处理节点] 错误已处理")
    state["route"] = "__end__"
    
    return state

# ==================== 6. 构建图（Graph）- 多节点工作流 ====================
def build_advanced_agent():
    """构建带多节点的智能体图"""
    workflow = StateGraph(AdvancedAgentState)
    
    # 添加所有节点
    workflow.add_node("router", router_node)              # 路由节点
    workflow.add_node("execute_tool", execute_tool_node)   # 工具执行节点
    workflow.add_node("validate", validate_node)           # 验证节点
    workflow.add_node("summarize", summarize_node)        # 总结节点
    workflow.add_node("error_handler", error_handler_node) # 错误处理节点
    
    # 设置入口点
    workflow.set_entry_point("router")
    
    # 添加条件边：从路由节点根据决策路由
    def route_decision(state):
        """根据路由节点的决策决定下一步"""
        return state.get("route", "error_handler")
    
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "execute_tool": "execute_tool",  # 需要工具 → 执行工具
            "summarize": "summarize",         # 不需要工具 → 直接总结
            "error_handler": "error_handler"  # 错误 → 错误处理
        }
    )
    
    # 从工具执行节点到验证节点
    workflow.add_edge("execute_tool", "validate")
    
    # 从验证节点根据验证结果路由
    def validate_decision(state):
        """根据验证结果决定下一步"""
        return state.get("route", "summarize")
    
    workflow.add_conditional_edges(
        "validate",
        validate_decision,
        {
            "execute_tool": "execute_tool",  # 需要重试 → 重新执行工具
            "summarize": "summarize",         # 验证通过 → 总结
            "error_handler": "error_handler"  # 验证失败 → 错误处理
        }
    )
    
    # 总结节点和错误处理节点都直接结束
    workflow.add_edge("summarize", END)
    workflow.add_edge("error_handler", END)
    
    return workflow.compile()

# ==================== 7. 运行智能体 ====================
def run_advanced_agent(query: str):
    """运行高级智能体"""
    print(f"\n{'='*60}")
    print(f"用户查询: {query}")
    print('='*60)
    
    # 初始化状态
    initial_state = AdvancedAgentState(
        messages=[HumanMessage(content=query)],
        selected_tool="",
        tool_input="",
        tool_result="",
        route="router"
    )
    
    # 构建图并执行
    graph = build_advanced_agent()
    final_state = graph.invoke(initial_state)
    
    # 提取最终答案
    messages = final_state["messages"]
    print(f"\n总共 {len(messages)} 条消息")
    
    # 显示对话历史
    for i, msg in enumerate(messages):
        role = "用户" if msg.type == "human" else "AI"
        content_preview = msg.content[:150] + ('...' if len(msg.content) > 150 else '')
        print(f"\n[{role}消息{i+1}] {content_preview}")
    
    # 返回最后一条AI消息
    for msg in reversed(messages):
        if msg.type == "ai":
            return msg.content
    
    return "没有生成回答"

# ==================== 8. 测试 ====================
if __name__ == "__main__":
    test_cases = [
        "计算一下 (25 + 17) × 3 等于多少？",
        "现在是什么时间？",
        "北京的天气怎么样？",
        "搜索一下 LangChain 的最新信息",
        "3的平方加上4的平方再开方是多少？",
        "介绍一下你自己"
    ]
    
    for i, test_query in enumerate(test_cases, 1):
        print(f"\n{'#'*60}")
        print(f"测试 {i}: {test_query}")
        print('#'*60)
        
        result = run_advanced_agent(test_query)
        print(f"\n最终答案:\n{result}")
        print("-" * 60)
