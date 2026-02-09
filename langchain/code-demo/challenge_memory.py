# 添加对话记忆功能
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

@dataclass
class ConversationMemory:
    """对话记忆数据类"""
    conversation_id: str
    user_id: str = "default"
    context_window: int = 10  # 记忆的对话轮数
    summary: str = ""  # 对话摘要
    entities: Dict[str, Any] = None  # 识别的实体
    preferences: List[str] = None  # 用户偏好
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.entities is None:
            self.entities = {}
        if self.preferences is None:
            self.preferences = []
    
    def to_dict(self):
        return asdict(self)
    
    def update(self, new_interaction: Dict[str, Any]):
        """更新记忆"""
        self.updated_at = datetime.now().isoformat()
        
        # 更新实体
        if "entities" in new_interaction:
            for key, value in new_interaction["entities"].items():
                self.entities[key] = value
        
        # 更新偏好
        if "preferences" in new_interaction:
            for pref in new_interaction["preferences"]:
                if pref not in self.preferences:
                    self.preferences.append(pref)
        
        # 如果对话太长，生成摘要
        if len(self.entities) > 20 or len(self.preferences) > 10:
            self._summarize()
    
    def _summarize(self):
        """生成记忆摘要"""
        # 简化的摘要逻辑，实际应该用LLM生成
        entity_summary = ", ".join(list(self.entities.keys())[:5])
        pref_summary = ", ".join(self.preferences[:3])
        self.summary = f"对话涉及: {entity_summary}。偏好: {pref_summary}"

class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, storage_path: str = "memory_storage.json"):
        self.storage_path = storage_path
        self.memories: Dict[str, ConversationMemory] = self._load_memories()
    
    def _load_memories(self) -> Dict[str, ConversationMemory]:
        """从文件加载记忆"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                memories = {}
                for conv_id, mem_data in data.items():
                    memories[conv_id] = ConversationMemory(**mem_data)
                return memories
            except Exception as e:
                print(f"加载记忆失败: {e}")
        return {}
    
    def save_memories(self):
        """保存记忆到文件"""
        try:
            data = {conv_id: memory.to_dict() 
                   for conv_id, memory in self.memories.items()}
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存记忆失败: {e}")
    
    def get_memory(self, conversation_id: str, user_id: str = "default") -> ConversationMemory:
        """获取或创建记忆"""
        if conversation_id not in self.memories:
            self.memories[conversation_id] = ConversationMemory(
                conversation_id=conversation_id,
                user_id=user_id
            )
        return self.memories[conversation_id]
    
    def extract_memory_context(self, conversation_id: str, current_query: str) -> str:
        """从记忆中提取相关上下文"""
        if conversation_id not in self.memories:
            return ""
        
        memory = self.memories[conversation_id]
        context_parts = []
        
        # 添加摘要
        if memory.summary:
            context_parts.append(f"对话摘要: {memory.summary}")
        
        # 添加上次提到的实体
        if memory.entities:
            recent_entities = list(memory.entities.items())[-3:]  # 最近3个实体
            if recent_entities:
                entity_str = ", ".join([f"{k}: {v}" for k, v in recent_entities])
                context_parts.append(f"最近提到的: {entity_str}")
        
        # 添加用户偏好
        if memory.preferences:
            prefs = ", ".join(memory.preferences[-3:])  # 最近3个偏好
            context_parts.append(f"用户偏好: {prefs}")
        
        return "\n".join(context_parts) if context_parts else ""

# ========== 集成记忆到LangGraph ==========
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class MemoryEnhancedState(TypedDict):
    """增强状态：包含记忆"""
    messages: Annotated[List, add_messages]
    conversation_id: str
    memory_context: str
    user_id: str
    next_node: str

def memory_enhanced_planning(state: MemoryEnhancedState):
    """带记忆的规划节点"""
    
    # 初始化记忆管理器
    memory_manager = MemoryManager()
    
    # 获取或创建记忆
    memory = memory_manager.get_memory(
        state["conversation_id"], 
        state["user_id"]
    )
    
    # 从记忆中提取上下文
    current_query = state["messages"][-1].content if state["messages"] else ""
    memory_context = memory_manager.extract_memory_context(
        state["conversation_id"], 
        current_query
    )
    
    state["memory_context"] = memory_context
    
    # 构建带记忆的提示词
    planning_prompt = f"""
    历史对话记忆：
    {memory_context}
    
    当前问题：{current_query}
    
    请考虑对话历史来回答或处理当前问题。
    """
    
    # 这里可以继续原来的规划逻辑，但加入记忆上下文
    # ... (使用planning_prompt替代原来的提示词)
    
    # 更新记忆（在实际响应后）
    # 这里需要提取当前对话的实体和偏好
    # 简化的实体提取
    entities = {}
    if "时间" in current_query:
        entities["时间查询"] = "用户询问时间相关"
    if "计算" in current_query or "等于" in current_query:
        entities["计算需求"] = "用户需要数学计算"
    
    memory.update({
        "entities": entities,
        "preferences": ["需要详细计算"] if "计算" in current_query else []
    })
    
    # 保存记忆
    memory_manager.save_memories()
    
    return state

# 使用示例
def test_memory_system():
    """测试记忆系统"""
    memory_manager = MemoryManager()
    
    # 模拟对话
    conversation_id = "test_conv_001"
    
    # 第一次对话
    memory = memory_manager.get_memory(conversation_id)
    memory.update({
        "entities": {"用户": "学习者", "兴趣": "AI编程"},
        "preferences": ["喜欢详细解释", "需要示例代码"]
    })
    
    # 提取记忆上下文
    context = memory_manager.extract_memory_context(conversation_id, "如何学习LangGraph？")
    print("记忆上下文:", context)
    
    # 保存
    memory_manager.save_memories()

# test_memory_system()