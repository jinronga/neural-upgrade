# demo.py - 你的第一个LangChain程序
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

# 从系统环境变量获取配置
ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

# 检查必要的环境变量
if not ARK_API_KEY:
    raise ValueError(
        "请设置环境变量 ARK_API_KEY。"
        "使用：export ARK_API_KEY='your-api-key'"
    )

llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
)

# 2. 创建一个提示词模板，{question} 是一个占位符
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有帮助的助手。请用中文回答，并尽量详细。"),
    ("human", "{question}")
])

# 3. 创建一个输出解析器，把AI的复杂响应转为简单字符串
output_parser = StrOutputParser()

# 4. 使用 LCEL（LangChain 表达式语言）的管道符 | 将它们组合成链
# 这是LangChain最核心、最优雅的编排方式！
chain = prompt | llm | output_parser    

# 5. 运行这条链，并提问！
# response = chain.invoke({"question": "请用一句话解释什么是 LangChain？"})
# print("AI的回答：", response)

# 你可以继续提问试试
response2 = chain.invoke({"question": "再解释一下什么是LangGraph？"})
print("AI的回答：", response2)