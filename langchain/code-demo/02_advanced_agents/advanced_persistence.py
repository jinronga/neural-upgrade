"""
advanced_persistence.py - 真实持久化存储

这里提供两种持久化记忆的示例实现：

1. PersistentMemory（Redis 版）
   - 适合存储会话状态快照 + 最近消息流水
2. MongoPersistentMemory（MongoDB 版，简化示例）
   - 适合更长期、结构化的对话数据存储

注意：
- 真正在线上使用时，请根据你的部署环境配置 redis_url / mongo_uri。
- 本文件不直接依赖你现有的 LangGraph 结构，只提供通用接口，
  方便在 complete_agent 的 memory 节点中接入。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - 仅在未安装 redis 时触发
    redis = None  # type: ignore

try:
    from pymongo import MongoClient  # type: ignore
except ImportError:  # pragma: no cover
    MongoClient = None  # type: ignore


# ========= 1. Redis 持久化实现 =========


@dataclass
class PersistentMemory:
    """基于 Redis 的持久化记忆。

    用途：
    - 保存完整会话状态快照（简化后的 state）
    - 维护最近的消息流水，用于重建上下文或做检索
    """

    redis_url: str = "redis://localhost:6379/0"
    expiry_days: int = 7  # 记忆保留天数

    def __post_init__(self) -> None:
        if redis is None:
            raise ImportError(
                "未安装 redis 库，请先执行：pip install redis"
            )
        self._client = redis.from_url(self.redis_url)
        self._expiry = timedelta(days=self.expiry_days)

    # ---- Key 约定 ----

    def _state_key(self, conv_id: str) -> str:
        return f"conv:{conv_id}:state"

    def _messages_key(self, conv_id: str) -> str:
        return f"conv:{conv_id}:messages"

    # ---- 状态快照 ----

    def save_conversation(self, conv_id: str, state: Dict[str, Any]) -> None:
        """保存对话状态快照。

        建议只保存「精简后的状态」，例如：
        - conversation_id / user_id
        - memory_context / 用户偏好
        - 最近几条消息的摘要
        """
        key = self._state_key(conv_id)
        data = {
            "state": state,
            "updated_at": datetime.now().isoformat(),
            "summary": self._generate_summary(state),
        }
        self._client.setex(
            key,
            int(self._expiry.total_seconds()),
            json.dumps(data, ensure_ascii=False),
        )

    def get_conversation(self, conv_id: str) -> Dict[str, Any]:
        """恢复对话状态快照。"""
        key = self._state_key(conv_id)
        raw = self._client.get(key)
        if not raw:
            return {}
        data = json.loads(raw)
        return data.get("state", {})

    # ---- 消息流水 ----

    def append_message(self, conv_id: str, message: Dict[str, Any]) -> None:
        """追加一条消息到该会话的消息列表。

        message 结构示例：
        {
            "role": "human" | "ai" | "tool",
            "content": "......",
            "metadata": {...}
        }
        """
        key = self._messages_key(conv_id)
        payload = {
            **message,
            "timestamp": datetime.now().isoformat(),
        }
        self._client.rpush(key, json.dumps(payload, ensure_ascii=False))
        # 为消息列表设置过期时间（与 state 一致）
        self._client.expire(key, int(self._expiry.total_seconds()))

    def get_recent_messages(
        self, conv_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取最近 N 条消息（按时间顺序）。"""
        key = self._messages_key(conv_id)
        # -limit:-1 取列表尾部的 N 条
        raw_list = self._client.lrange(key, -limit, -1)
        return [json.loads(x) for x in raw_list]

    # ---- 语义搜索（占位实现） ----

    def search_memories(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """语义搜索历史对话（示意接口）。

        实际使用时，推荐接入向量数据库（如 Chroma / FAISS / Qdrant / Pinecone）：
        1. 写入时，对每条消息做 embedding，存入向量库，metadata 里带上 conv_id / role / timestamp。
        2. 搜索时，对 query 做 embedding，然后在向量库里做相似度检索，返回 top-k 结果。

        这里为了保持示例简单，只返回最近的若干条消息，
        方便你先打通调用链，再逐步接入向量检索。
        """
        # 简单实现：直接返回最近的消息，真实项目中请替换为向量搜索结果
        return self.get_recent_messages(conv_id="*", limit=limit)  # type: ignore[arg-type]

    # ---- 内部辅助 ----

    def _generate_summary(self, state: Dict[str, Any]) -> str:
        """根据 state 生成一个非常简短的摘要（占位实现）。

        真实系统里，可以考虑：
        - 把最近 N 条消息拼接后，交给 LLM 生成摘要；
        - 或者根据 memory_context / entities / preferences 生成用户画像。
        """
        try:
            # 优先使用已有的 memory_context
            ctx = state.get("memory_context")
            if isinstance(ctx, str) and ctx.strip():
                return ctx[:200]

            # 其次尝试从 messages 中提取最后一条
            msgs = state.get("messages") or []
            if msgs:
                last = msgs[-1]
                content = getattr(last, "content", "") or str(last)
                return f"最近消息: {content[:180]}"

            # 兜底：截断整个 state 的 JSON
            return json.dumps(state, ensure_ascii=False)[:200]
        except Exception:
            return ""


# ========= 2. MongoDB 持久化实现（可选） =========


@dataclass
class MongoPersistentMemory:
    """基于 MongoDB 的持久化记忆（简化示例）。

    推荐用在需要：
    - 长期保存大量对话数据
    - 按用户 / 会话维度做统计或分析
    的场景。
    """

    mongo_uri: str = "mongodb://localhost:27017"
    db_name: str = "agent_memory"
    conv_collection: str = "conversations"

    def __post_init__(self) -> None:
        if MongoClient is None:
            raise ImportError(
                "未安装 pymongo 库，请先执行：pip install pymongo"
            )
        self._client = MongoClient(self.mongo_uri)
        self._db = self._client[self.db_name]
        self._convs = self._db[self.conv_collection]

    def save_conversation(self, conv_id: str, state: Dict[str, Any]) -> None:
        """保存或更新会话文档。"""
        doc = {
            "conv_id": conv_id,
            "state": state,
            "updated_at": datetime.now(),
        }
        self._convs.update_one(
            {"conv_id": conv_id},
            {"$set": doc, "$setOnInsert": {"created_at": datetime.now()}},
            upsert=True,
        )

    def get_conversation(self, conv_id: str) -> Dict[str, Any]:
        """读取会话文档。"""
        doc = self._convs.find_one({"conv_id": conv_id})
        if not doc:
            return {}
        return doc.get("state", {})

    def search_memories(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """关键词搜索会话（示意接口）。

        实际项目中，建议：
        - 将 messages 独立成一个 collection，存储每条消息；
        - 对 message.content 建立全文索引或使用外部向量库做语义检索。
        """
        # 这里做一个非常粗糙的「按 state 里包含关键字」搜索示例
        cursor = self._convs.find(
            {"$text": {"$search": query}}  # 需要在 Mongo 上对相应字段建 text index
        ).limit(limit)
        return list(cursor)

