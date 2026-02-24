from __future__ import annotations

from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.services import usage_service


class UsageQueryInput(BaseModel):
    """Input schema for querying user usage."""

    user_id: str = Field(description="用户ID")


class QueryUsageTool(BaseTool):
    """LangChain tool that queries realtime usage for a user."""

    name = "query_usage"
    description = "查询用户的实时流量、语音使用情况"
    args_schema: Type[BaseModel] = UsageQueryInput

    def __init__(self, db_session_factory: sessionmaker, **kwargs):
        super().__init__(**kwargs)
        self._db_session_factory = db_session_factory

    def _run(self, user_id: str) -> str:
        try:
            user_id_int = int(user_id)
        except ValueError:
            return "无效的用户ID，请提供数字格式的用户ID。"

        db: Session = self._db_session_factory()
        try:
            current_mb = usage_service.get_current_usage(db, user_id_int, redis_client=None)
        finally:
            db.close()

        return f"用户 {user_id_int} 当前总流量使用约为 {current_mb:.2f} MB。"

    async def _arun(self, user_id: str) -> str:  # pragma: no cover - sync only
        raise NotImplementedError("QueryUsageTool 暂不支持异步调用。")

