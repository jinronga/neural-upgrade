import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
import math


# 手动实现工具描述函数（替代 render_text_description）
def render_text_description(tools):
    """将工具列表转换为文本描述"""
    descriptions = []
    for t in tools:
        desc = f"- {t.name}: {t.description}"
        descriptions.append(desc)
    return "\n".join(descriptions)


# 1. 定义工具 - 就像给AI安装插件
@tool
def calculator(expression: str) -> str:
    """执行数学计算。支持加减乘除、平方、开方等。
    示例: '2 + 3 * 4' 或 'sqrt(16)' 或 'pow(2, 3)'"""
    try:
        # 安全评估数学表达式
        allowed_names = {
            'abs': abs, 'round': round, 'pow': pow, 
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'pi': math.pi, 'e': math.e
        }
        # 替换常见数学符号
        expression = expression.replace('^', '**').replace('×', '*').replace('÷', '/')
        result = eval(expression, {"__builtins__": {}}, {**allowed_names, 'math': math})
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}，请检查表达式格式"

@tool
def get_current_time() -> str:
    """获取当前日期和时间。"""
    from datetime import datetime
    now = datetime.now()
    return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')}"

# 2. 创建工具列表
tools = [calculator, get_current_time]
tools_dict = {t.name: t for t in tools}


ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

# 3. 使用自定义API创建模型
llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
    temperature=0.1,  # 工具调用需要更确定的输出
)

# 4. 创建提示词 - 告诉AI如何使用工具
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个有帮助的AI助手，可以使用工具来帮助用户。
    你可以使用的工具：
    {tools}
    
    使用规则：
    1. 如果用户的问题需要计算，使用calculator工具
    2. 如果用户询问时间，使用get_current_time工具
    3. 其他情况直接回答
    
    请严格按照以下格式响应：
    思考：[分析用户问题，决定是否使用工具]
    工具：[如果需要使用工具，写工具名称]
    工具输入：[如果需要使用工具，写输入内容]
    最终答案：[给用户的回答]
    """),
    ("human", "{input}")
])

# 5. 手动处理工具调用的简单链
def simple_agent_chain(user_input: str):
    """一个简单的工具调用流程"""
    print(f"\n用户问题: {user_input}")
    
    # 第一步：让AI思考
    tools_description = render_text_description(tools)
    messages = prompt.format_messages(input=user_input, tools=tools_description)
    ai_response = llm.invoke(messages).content
    
    print(f"AI思考:\n{ai_response}")
    
    # 第二步：解析AI响应，看是否需要调用工具
    if "工具: calculator" in ai_response:
        # 提取计算表达式
        import re
        match = re.search(r"工具输入: (.+)", ai_response)
        if match:
            expression = match.group(1).strip()
            print(f"调用计算器，表达式: {expression}")
            result = calculator.invoke(expression)
            print(f"工具返回: {result}")
            
            # 第三步：把工具结果给AI，生成最终回答
            follow_up_prompt = f"""
            用户原问题: {user_input}
            工具计算结果: {result}
            请基于工具结果给出最终回答。"""
            
            final_response = llm.invoke(follow_up_prompt)
            return final_response.content
    
    return ai_response

# 6. 测试
if __name__ == "__main__":
    test_questions = [
        "计算一下 (25 + 17) × 3 等于多少？",
        "现在是什么时间？",
        "3的平方加上4的平方再开方是多少？",
        "介绍一下LangChain"
    ]
    
    for question in test_questions:
        answer = simple_agent_chain(question)
        print(f"最终答案: {answer}")
        print("-" * 50)