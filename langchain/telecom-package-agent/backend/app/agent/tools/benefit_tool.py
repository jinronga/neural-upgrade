from __future__ import annotations

from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.services import benefit_service


class GetPendingBenefitsInput(BaseModel):
    """Input schema for querying pending benefits."""

    user_id: str = Field(description="用户ID")


class ClaimBenefitInput(BaseModel):
    """Input schema for claiming a benefit."""

    user_id: str = Field(description="用户ID")
    benefit_id: int = Field(description="权益ID")
    channel: str = Field(description="领取渠道，例如 app、客服 或 活动页面")


class GetPendingBenefitsTool(BaseTool):
    """LangChain tool that returns benefits a user can still claim."""

    name = "get_pending_benefits"
    description = "查询用户尚未领取的可用权益"
    args_schema: Type[BaseModel] = GetPendingBenefitsInput

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
            benefits = benefit_service.get_pending_benefits(db, user_id_int)
        finally:
            db.close()

        if not benefits:
            return "当前没有可领取的权益。"

        lines: list[str] = ["你可以领取以下权益："]
        for b in benefits:
            lines.append(f"- {b.name}：{b.description or '暂无描述'}")
        return "\n".join(lines)

    async def _arun(self, user_id: str) -> str:  # pragma: no cover - sync only
        raise NotImplementedError("GetPendingBenefitsTool 暂不支持异步调用。")


class ClaimBenefitTool(BaseTool):
    """LangChain tool that claims a specific benefit for a user."""

    name = "claim_benefit"
    description = "为用户领取指定权益"
    args_schema: Type[BaseModel] = ClaimBenefitInput

    def __init__(self, db_session_factory: sessionmaker, **kwargs):
        super().__init__(**kwargs)
        self._db_session_factory = db_session_factory

    def _run(self, user_id: str, benefit_id: int, channel: str) -> str:
        try:
            user_id_int = int(user_id)
        except ValueError:
            return "无效的用户ID，请提供数字格式的用户ID。"

        db: Session = self._db_session_factory()
        try:
            record = benefit_service.claim_benefit(
                db, user_id=user_id_int, benefit_id=benefit_id, channel=channel
            )
        finally:
            db.close()

        if record is None:
            return "领取权益失败，可能是用户不存在、权益无效、库存不足或已领取过。"

        return f"已为用户 {user_id_int} 成功领取权益（ID={benefit_id}），当前状态：{record.status}。"

    async def _arun(self, user_id: str, benefit_id: int, channel: str) -> str:  # pragma: no cover
        raise NotImplementedError("ClaimBenefitTool 暂不支持异步调用。")

