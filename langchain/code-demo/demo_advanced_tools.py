import requests
from langchain.tools import Tool

# 添加网络搜索工具（需要安装：pip install duckduckgo-search）
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
    except Exception as e:
        return f"搜索失败: {str(e)}"

# 添加天气查询工具（示例，需要真实API）
@tool
def get_weather(city: str) -> str:
    """获取城市天气信息。"""
    # 这里使用模拟数据，真实项目可以接入天气API
    weather_data = {
        "北京": "晴，15°C，空气质量良",
        "上海": "多云，18°C，空气质量优", 
        "广州": "阵雨，22°C，空气质量良",
        "深圳": "晴，24°C，空气质量优"
    }
    return weather_data.get(city, f"暂无{city}的天气信息")

# 在LangGraph中使用这些工具
def build_advanced_agent():
    """构建带多种工具的智能体"""
    
    # 所有工具
    all_tools = [calculator, get_current_time, web_search, get_weather]
    
    # 修改提示词以包含所有工具
    advanced_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个强大的AI助手，可以使用多种工具。
        可用工具：
        {tools}
        
        请根据问题选择合适的工具。
        如果问题需要最新信息，使用web_search。
        如果问天气，使用get_weather。
        如果问计算，使用calculator。
        如果问时间，使用get_current_time。
        
        工具调用格式：
        {{
            "tool": "工具名",
            "tool_input": "输入"
        }}"""),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # 这里可以接着构建更智能的图...
    # （基于前面的代码扩展）