# 多工具连续调用
from typing import TypedDict, List, Annotated, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import json
import os

# ========== 1. 增强的状态定义 ==========
class MultiToolState(TypedDict):
    """支持多工具调用的状态"""
    messages: Annotated[List, add_messages]  # 对话历史
    tool_calls: List[Dict[str, Any]]  # 本次会话的所有工具调用记录
    pending_tools: List[Dict[str, Any]]  # 待执行工具队列
    current_step: str  # 当前步骤描述
    max_steps: int  # 最大步骤限制
    step_count: int  # 已执行步骤计数

# ========== 2. 增强的工具集 ==========
from langchain.tools import tool
from datetime import datetime
import math
import os

@tool
def calculator(expression: str) -> float:
    """执行数学计算，返回数值结果。支持 +, -, *, /, ^, sqrt(), sin(), cos() 等"""
    try:
        # 安全计算环境
        safe_dict = {
            'abs': abs, 'round': round, 'pow': pow, 
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'tan': math.tan, 'log': math.log, 'log10': math.log10,
            'pi': math.pi, 'e': math.e, 'radians': math.radians,
            'degrees': math.degrees
        }
        
        # 替换常见数学符号
        expr = expression.replace('^', '**').replace('×', '*').replace('÷', '/')
        expr = expr.replace('π', 'pi').replace('Π', 'pi')
        
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        return float(result)
    except Exception as e:
        raise ValueError(f"计算错误: {expression} -> {str(e)}")

@tool
def get_current_time(format: str = "full") -> str:
    """获取当前时间。format可选: 'full'(完整), 'date'(仅日期), 'time'(仅时间)"""
    now = datetime.now()
    if format == "date":
        return now.strftime("%Y年%m月%d日")
    elif format == "time":
        return now.strftime("%H:%M:%S")
    else:
        return now.strftime("%Y年%m月%d日 %H:%M:%S")

@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> float:
    """单位转换器。支持: 长度(m, km, cm, mm), 重量(kg, g, lb), 温度(C, F, K)"""
    conversions = {
        # 长度
        ("m", "km"): lambda x: x / 1000,
        ("km", "m"): lambda x: x * 1000,
        ("m", "cm"): lambda x: x * 100,
        ("cm", "m"): lambda x: x / 100,
        
        # 重量
        ("kg", "g"): lambda x: x * 1000,
        ("g", "kg"): lambda x: x / 1000,
        ("kg", "lb"): lambda x: x * 2.20462,
        ("lb", "kg"): lambda x: x / 2.20462,
        
        # 温度（需要特殊处理）
        ("C", "F"): lambda x: (x * 9/5) + 32,
        ("F", "C"): lambda x: (x - 32) * 5/9,
        ("C", "K"): lambda x: x + 273.15,
        ("K", "C"): lambda x: x - 273.15,
    }
    
    if from_unit == to_unit:
        return value
    
    key = (from_unit, to_unit)
    if key in conversions:
        return round(conversions[key](value), 6)
    
    # 温度的特殊情况
    if from_unit == "F" and to_unit == "K":
        return round((value - 32) * 5/9 + 273.15, 6)
    if from_unit == "K" and to_unit == "F":
        return round((value - 273.15) * 9/5 + 32, 6)
    
    raise ValueError(f"不支持从 {from_unit} 转换到 {to_unit}")

@tool
def currency_converter(amount: float, from_currency: str, to_currency: str) -> str:
    """货币转换器（使用模拟汇率）。支持: USD, CNY, EUR, JPY, GBP"""
    # 注意：这是模拟数据，真实项目需要接入API
    rates = {
        "USD": {"CNY": 7.2, "EUR": 0.92, "JPY": 150, "GBP": 0.79},
        "CNY": {"USD": 0.14, "EUR": 0.13, "JPY": 20.8, "GBP": 0.11},
        "EUR": {"USD": 1.09, "CNY": 7.83, "JPY": 163, "GBP": 0.86},
    }
    
    if from_currency == to_currency:
        return f"{amount} {from_currency}"
    
    if from_currency in rates and to_currency in rates[from_currency]:
        rate = rates[from_currency][to_currency]
        result = amount * rate
        return f"{amount} {from_currency} = {result:.2f} {to_currency} (汇率: {rate})"
    
    # 尝试反向查找
    for base_currency, targets in rates.items():
        if to_currency in targets and from_currency in targets.values():
            # 这里简化处理
            return f"暂不支持 {from_currency} 到 {to_currency} 的直接转换"
    
    return f"暂不支持 {from_currency} 或 {to_currency}"

@tool
def realtime_search(query: str) -> str:
    """实时搜索最新信息（DuckDuckGo 简单封装）"""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "搜索功能需要安装 duckduckgo-search：pip install duckduckgo-search"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "没有找到相关信息。"
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. {r.get('title', '')}\n{r.get('body', '')}\n{r.get('href', '')}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"搜索失败: {e}"


@tool
def read_file(filepath: str) -> str:
    """读取项目内文本文件内容（相对路径，带简单安全限制）"""
    try:
        # 禁止绝对路径和上级目录，避免误读系统文件
        if filepath.startswith("/") or ".." in filepath:
            return "出于安全考虑，不支持读取绝对路径或上级目录的文件。"

        base_dir = os.path.dirname(__file__)
        full_path = os.path.join(base_dir, filepath)

        if not os.path.exists(full_path):
            return f"文件不存在: {filepath}"

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        if len(content) > 4000:
            return content[:4000] + "\n...\n(内容过长，已截断)"
        return content
    except Exception as e:
        return f"读取文件失败: {e}"


# 工具集合
tools = [
    calculator,
    get_current_time,
    unit_converter,
    currency_converter,
    realtime_search,
    read_file,
]
tools_dict = {tool.name: tool for tool in tools}

# ========== 3. 初始化LLM ==========
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 参考 demo_advanced_tools 的 ARK 配置
ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
    temperature=0.1,
)


def render_text_description(tools):
    """将工具列表转换为文本描述"""
    descriptions = []
    for t in tools:
        desc = f"- {t.name}: {t.description}"
        descriptions.append(desc)
    return "\n".join(descriptions)

# ========== 4. 智能规划节点 ==========
def planning_node(state: MultiToolState):
    """规划节点：分析问题并生成多步骤执行计划"""
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    
    print(f"\n{'='*50}")
    print("[规划节点] 分析复杂问题...")
    
    # 构建规划提示
    tools_desc = render_text_description(tools)
    user_query = state["messages"][-1].content if state["messages"] else ""
    
    planning_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=f"""你是一个任务规划专家。请分析用户的问题，拆解为多个步骤，每个步骤可能需要使用工具。
        
可用工具：
{tools_desc}

请按照以下JSON格式规划步骤：
{{
    "analysis": "问题分析",
    "steps": [
        {{
            "step": 1,
            "description": "步骤描述",
            "tool_required": true/false,
            "tool_name": "工具名（如果需要）",
            "tool_input": {{"参数": "值"}},
            "depends_on": []  # 依赖的步骤编号
        }}
    ],
    "expected_output": "最终输出形式"
}}

示例：
问题："现在的时间加上30分钟是多少？"
规划：{{
    "analysis": "需要先获取当前时间，然后计算30分钟后的时间",
    "steps": [
        {{"step": 1, "description": "获取当前时间", "tool_required": true, "tool_name": "get_current_time", "tool_input": {{"format": "time"}}, "depends_on": []}},
        {{"step": 2, "description": "将30分钟转换为秒", "tool_required": true, "tool_name": "calculator", "tool_input": {{"expression": "30 * 60"}}, "depends_on": []}},
        {{"step": 3, "description": "计算最终时间", "tool_required": false, "tool_name": null, "tool_input": {{}}, "depends_on": [1, 2]}}
    ],
    "expected_output": "时间字符串"
}}"""),
        HumanMessage(content=f"用户问题：{user_query}")
    ])
    
    # 获取规划
    response = llm.invoke(planning_prompt.format_messages())
    
    try:
        plan = json.loads(response.content)
        print(f"[规划完成] 拆分为 {len(plan['steps'])} 个步骤")
        
        # 初始化待执行队列（只包含不依赖其他步骤的步骤）
        pending_tools = []
        for step in plan["steps"]:
            if step.get("tool_required", False):
                pending_tools.append({
                    "step": step["step"],
                    "description": step["description"],
                    "tool_name": step["tool_name"],
                    "tool_input": step["tool_input"]
                })
        
        # 更新状态
        state["pending_tools"] = pending_tools
        state["current_step"] = f"规划完成：{plan['analysis']}"
        state["step_count"] = 0
        state["tool_calls"].append({
            "type": "planning",
            "plan": plan,
            "timestamp": datetime.now().isoformat()
        })
        
        # 将规划结果添加到消息历史
        state["messages"].append(AIMessage(content=f"规划分析：{plan['analysis']}"))
        
        # 如果有待执行工具，去执行节点；否则直接去回答节点
        if pending_tools:
            state["next_node"] = "execution"
        else:
            state["next_node"] = "answer"
            
    except json.JSONDecodeError as e:
        print(f"[规划失败] JSON解析错误: {e}")
        state["next_node"] = "answer"
    
    return state

# ========== 5. 工具执行节点 ==========
def execution_node(state: MultiToolState):
    """执行节点：从队列中取出并执行工具"""
    print(f"\n[执行节点] 执行工具...")
    
    if not state["pending_tools"]:
        print("[执行节点] 没有待执行工具")
        state["next_node"] = "answer"
        return state
    
    # 取出第一个工具
    tool_task = state["pending_tools"].pop(0)
    step_num = tool_task["step"]
    tool_name = tool_task["tool_name"]
    tool_input = tool_task["tool_input"]
    
    print(f"[执行步骤 {step_num}] {tool_task['description']}")
    print(f"  使用工具: {tool_name}")
    print(f"  输入参数: {tool_input}")
    
    try:
        # 执行工具
        if tool_name in tools_dict:
            # 将字典参数展开为关键字参数
            if isinstance(tool_input, dict):
                result = tools_dict[tool_name].invoke(tool_input)
            else:
                # 如果不是字典，转为字符串
                result = tools_dict[tool_name].invoke(str(tool_input))
            
            # 记录结果
            tool_record = {
                "step": step_num,
                "tool": tool_name,
                "input": tool_input,
                "output": str(result),
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            state["tool_calls"].append(tool_record)
            state["step_count"] += 1
            
            print(f"  执行结果: {result}")
            
            # 将结果添加到消息历史
            from langchain_core.messages import AIMessage
            result_msg = f"步骤{step_num}完成：{tool_task['description']}\n结果：{result}"
            state["messages"].append(AIMessage(content=result_msg))
            
        else:
            print(f"  错误：未知工具 {tool_name}")
            state["tool_calls"].append({
                "step": step_num,
                "tool": tool_name,
                "input": tool_input,
                "output": f"错误：未知工具 {tool_name}",
                "success": False
            })
            
    except Exception as e:
        print(f"  工具执行失败: {e}")
        state["tool_calls"].append({
            "step": step_num,
            "tool": tool_name,
            "input": tool_input,
            "output": f"错误：{str(e)}",
            "success": False
        })
    
    # 检查是否继续执行
    if state["pending_tools"] and state["step_count"] < state.get("max_steps", 10):
        # 还有工具待执行，继续执行
        state["next_node"] = "execution"
    else:
        # 执行完成，去回答
        state["next_node"] = "answer"
    
    return state

# ========== 6. 回答生成节点 ==========
def answer_node(state: MultiToolState):
    """回答节点：基于所有结果生成最终回答"""
    print(f"\n[回答节点] 生成最终回答...")
    
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # 准备工具执行历史
    tool_history = ""
    for call in state["tool_calls"]:
        if call.get("type") != "planning":
            status = "✓" if call.get("success", False) else "✗"
            tool_history += f"步骤{call.get('step', '?')}: {call.get('tool', '未知')} -> {call.get('output', '无输出')} {status}\n"
    
    # 构建最终回答提示
    user_query = state["messages"][0].content if state["messages"] else ""
    
    answer_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=f"""基于以下工具执行结果，生成对用户问题的最终回答。
        
原始问题：{user_query}

工具执行历史：
{tool_history}

请生成一个自然、完整的回答，包含所有相关计算结果。"""),
        HumanMessage(content="请基于以上信息给出最终回答")
    ])
    
    # 生成最终回答
    response = llm.invoke(answer_prompt.format_messages())
    final_answer = response.content
    
    # 添加到消息历史
    from langchain_core.messages import AIMessage
    state["messages"].append(AIMessage(content=final_answer))
    
    print(f"[最终回答]\n{final_answer}")
    state["next_node"] = "__end__"
    
    return state

# ========== 7. 构建多工具工作流 ==========
def build_multi_tool_graph():
    """构建支持多工具连续调用的工作流图"""
    
    workflow = StateGraph(MultiToolState)
    
    # 添加节点
    workflow.add_node("planning", planning_node)      # 规划
    workflow.add_node("execution", execution_node)    # 执行
    workflow.add_node("answer", answer_node)          # 回答
    
    # 设置入口点
    workflow.set_entry_point("planning")
    
    # 定义路由函数
    def route_next(state):
        return state.get("next_node", "__end__")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "planning",
        route_next,
        {
            "execution": "execution",
            "answer": "answer",
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "execution", 
        route_next,
        {
            "execution": "execution",  # 继续执行下一个工具
            "answer": "answer",        # 执行完成，去回答
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "answer",
        route_next,
        {
            "__end__": END
        }
    )
    
    return workflow.compile()

# ========== 8. 测试函数 ==========
def test_multi_tool():
    """测试多工具调用"""
    
    test_cases = [
        "现在的时间加上30分钟是多少？",
        "把5公里转换成米，再加上500厘米，一共是多少米？",
        "计算圆的面积，半径是7.5厘米，结果用平方毫米表示",
        "100美元换成人民币，然后加上500欧元换成的人民币，一共是多少人民币？"
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n{'#'*60}")
        print(f"测试案例 {i}: {query}")
        print('#'*60)
        
        # 初始化状态
        from langchain_core.messages import HumanMessage
        initial_state = MultiToolState(
            messages=[HumanMessage(content=query)],
            tool_calls=[],
            pending_tools=[],
            current_step="开始",
            max_steps=10,
            step_count=0,
            next_node="planning"
        )
        
        # 构建并执行图
        graph = build_multi_tool_graph()
        final_state = graph.invoke(initial_state)
        
        # 打印工具调用历史
        print(f"\n工具调用历史:")
        for call in final_state["tool_calls"]:
            if call.get("type") == "planning":
                print(f"  📝 规划: {call.get('plan', {}).get('analysis', '')}")
            else:
                status = "✓" if call.get("success", False) else "✗"
                print(f"  {status} 步骤{call.get('step', '?')}: {call.get('tool', '未知')}")
                print(f"     输入: {call.get('input', '无')}")
                print(f"     输出: {call.get('output', '无')}")
        
        print(f"\n总共执行 {final_state['step_count']} 个步骤")
        print("="*60)

if __name__ == "__main__":
    test_multi_tool()