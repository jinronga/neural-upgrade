from __future__ import annotations

from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.models import Complaint, User


class HandleComplaintInput(BaseModel):
    """Input schema for handling a user complaint."""

    user_id: str = Field(description="用户ID")
    title: str = Field(description="投诉标题")
    content: str = Field(description="投诉详细内容")


class HandleComplaintTool(BaseTool):
    """LangChain tool that creates a complaint ticket for the user."""

    name = "handle_complaint"
    description = "为用户创建投诉工单并记录问题"
    args_schema: Type[BaseModel] = HandleComplaintInput

    def __init__(self, db_session_factory: sessionmaker, **kwargs):
        super().__init__(**kwargs)
        self._db_session_factory = db_session_factory

    def _run(self, user_id: str, title: str, content: str) -> str:
        try:
            user_id_int = int(user_id)
        except ValueError:
            return "无效的用户ID，请提供数字格式的用户ID。"

        db: Session = self._db_session_factory()
        try:
            user = db.get(User, user_id_int)
            if not user:
                return "未找到该用户，无法创建投诉工单。"

            complaint = Complaint(
                user_id=user_id_int,
                title=title,
                content=content,
                status="open",
            )
            db.add(complaint)
            db.commit()
            db.refresh(complaint)
        finally:
            db.close()

        return (
            f"已为用户 {user_id_int} 创建投诉工单（编号：{complaint.id}），"
            "我们会尽快为你处理，请保持电话畅通。"
        )

    async def _arun(self, user_id: str, title: str, content: str) -> str:  # pragma: no cover
        raise NotImplementedError("HandleComplaintTool 暂不支持异步调用。")

