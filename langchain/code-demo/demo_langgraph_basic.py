import os
from typing import TypedDict, List, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import operator


# 1. 定义状态（State）- 工作流的"记忆系统"
class AgentState(TypedDict):
    """定义工作流的状态结构"""
    messages: Annotated[List, add_messages]  # 对话消息历史
    next: Literal["agent", "tools", "__end__"]  # 下一步去哪

# 2. 重新定义工具（与前面相同）
@tool
def calculator(expression: str) -> str:
    """执行数学计算。"""
    try:
        allowed_names = {'abs': abs, 'round': round, 'pow': pow, 'sqrt': __import__('math').sqrt}
        expression = expression.replace('^', '**').replace('×', '*').replace('÷', '/')
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@tool 
def get_current_time() -> str:
    """获取当前时间。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

tools = [calculator, get_current_time]
tools_dict = {tool.name: tool for tool in tools}

# 3. 创建模型
from langchain_openai import ChatOpenAI

ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
    temperature=0.1,
)

# 4. 绑定工具到模型
from langchain.tools.render import render_text_description
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 创建带工具调用能力的LLM
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个有帮助的助手，可以使用工具。
    可用的工具: {tools}
    
    如果用户的问题需要工具，请严格按照以下JSON格式响应：
    {{
        "tool": "工具名称",
        "tool_input": "工具输入"
    }}
    
    如果不需要工具，直接回答。"""),
    MessagesPlaceholder(variable_name="messages"),
])

# 5. 创建各个节点（Node）
def agent_node(state: AgentState):
    """Agent节点：思考并决定行动"""
    print("\n[Agent节点] 正在思考...")
    
    # 准备工具描述
    tools_description = render_text_description(tools)
    
    # 调用LLM
    messages = state["messages"]
    response = llm.invoke(prompt.format_messages(
        tools=tools_description,
        messages=messages
    ))
    
    # 添加到消息历史
    state["messages"].append(response)
    
    # 检查是否要调用工具
    try:
        # 尝试解析工具调用
        import json
        content = response.content.strip()
        if content.startswith("{") and content.endswith("}"):
            tool_call = json.loads(content)
            if "tool" in tool_call:
                print(f"[Agent节点] 决定使用工具: {tool_call['tool']}")
                state["next"] = "tools"
                return state
    except:
        pass
    
    # 不需要工具，直接结束
    print("[Agent节点] 直接回答，无需工具")
    state["next"] = "__end__"
    return state

def tools_node(state: AgentState):
    """Tools节点：执行工具"""
    print("\n[Tools节点] 执行工具...")
    
    # 获取最后一条消息（应该是工具调用）
    last_message = state["messages"][-1]
    
    try:
        import json
        tool_call = json.loads(last_message.content)
        tool_name = tool_call.get("tool")
        tool_input = tool_call.get("tool_input", "")
        
        if tool_name in tools_dict:
            print(f"[Tools节点] 执行 {tool_name}，输入: {tool_input}")
            result = tools_dict[tool_name].invoke(tool_input)
            print(f"[Tools节点] 工具返回: {result}")
            
            # 将结果添加到消息历史
            from langchain_core.messages import AIMessage
            state["messages"].append(AIMessage(content=f"工具执行结果: {result}"))
        else:
            error_msg = f"未知工具: {tool_name}"
            state["messages"].append(AIMessage(content=error_msg))
    except Exception as e:
        error_msg = f"工具调用失败: {str(e)}"
        state["messages"].append(AIMessage(content=error_msg))
    
    # 执行完工具后，返回Agent节点继续思考
    state["next"] = "agent"
    return state

# 6. 构建图（Graph）
def build_agent_graph():
    """构建工作流图"""
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    
    # 设置入口点
    workflow.set_entry_point("agent")
    
    # 添加条件边（Conditional Edge）
    def decide_next_step(state):
        """根据状态决定下一步"""
        return state.get("next", "__end__")
    
    workflow.add_conditional_edges(
        "agent",
        decide_next_step,
        {
            "tools": "tools",  # 需要工具 -> 去tools节点
            "__end__": END     # 结束 -> 直接结束
        }
    )
    
    # tools节点执行完后总是返回agent节点
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()

# 7. 运行工作流
def run_agent(query: str):
    """运行智能体"""
    print(f"\n{'='*60}")
    print(f"用户查询: {query}")
    print('='*60)
    
    # 初始化状态
    from langchain_core.messages import HumanMessage
    initial_state = AgentState(
        messages=[HumanMessage(content=query)],
        next="agent"
    )
    
    # 构建图并执行
    graph = build_agent_graph()
    final_state = graph.invoke(initial_state)
    
    # 提取最终答案
    messages = final_state["messages"]
    print(f"\n总共 {len(messages)} 条消息")
    
    # 显示对话历史
    for i, msg in enumerate(messages):
        role = "用户" if msg.type == "human" else "AI"
        print(f"\n[{role}消息{i+1}]")
        print(f"{msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")
    
    # 返回最后一条AI消息
    for msg in reversed(messages):
        if msg.type == "ai":
            return msg.content
    
    return "没有生成回答"

# 8. 测试
if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "计算一下圆的面积，半径是5，使用π",
        "现在是什么时间？",
        "计算 (12 + 8) × 3 ÷ 4",
        "介绍一下你自己"
    ]
    
    for i, test_query in enumerate(test_cases, 1):
        print(f"\n{'#'*60}")
        print(f"测试 {i}: {test_query}")
        print('#'*60)
        
        result = run_agent(test_query)
        print(f"\n最终答案:\n{result}")