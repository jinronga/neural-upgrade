from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, List

from redis import Redis


@dataclass
class ConversationMessage:
    role: str
    content: str
    timestamp: float


class ConversationMemory:
    """Redis-based conversation memory for storing chat history.

    Each conversation is stored as a Redis list under a key:
      {key_prefix}:{session_id}
    """

    def __init__(
        self,
        redis_client: Redis,
        ttl_seconds: int = 60 * 60,
        key_prefix: str = "conv",
    ) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

    def _key(self, session_id: str) -> str:
        return f"{self.key_prefix}:{session_id}"

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the conversation and refresh TTL."""
        payload = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        key = self._key(session_id)
        self.redis.rpush(key, json.dumps(payload, ensure_ascii=False))
        self.redis.expire(key, self.ttl_seconds)

    def get_recent_messages(self, session_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Return the last N messages for a conversation."""
        key = self._key(session_id)
        # -limit:-1 will return up to limit latest entries
        raw_items: Iterable[bytes] = self.redis.lrange(key, -limit, -1)
        messages: List[ConversationMessage] = []
        for item in raw_items:
            try:
                data: Any = json.loads(item.decode("utf-8"))
                messages.append(
                    ConversationMessage(
                        role=str(data.get("role", "")),
                        content=str(data.get("content", "")),
                        timestamp=float(data.get("timestamp", time.time())),
                    )
                )
            except Exception:
                continue
        return messages

    def clear(self, session_id: str) -> None:
        """Delete all messages for a given conversation."""
        key = self._key(session_id)
        self.redis.delete(key)

    def cleanup_expired(self) -> int:
        """Best-effort cleanup of expired conversations.

        When TTL is set, Redis 会自动删除过期 key，这里仅作为补充：
        扫描所有会话 key，删除 TTL 已经过期（<0）的 key。
        """
        removed = 0
        pattern = f"{self.key_prefix}:*"
        for key in self.redis.scan_iter(match=pattern):
            ttl = self.redis.ttl(key)
            if ttl is not None and ttl < 0:
                self.redis.delete(key)
                removed += 1
        return removed

