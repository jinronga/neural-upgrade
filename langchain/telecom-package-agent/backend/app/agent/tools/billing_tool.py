from __future__ import annotations

from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.services import billing_service


class BillingQueryInput(BaseModel):
    """Input schema for querying realtime balance."""

    user_id: str = Field(description="用户ID")


class RefundInput(BaseModel):
    """Input schema for processing a refund."""

    user_id: str = Field(description="用户ID")
    amount: float = Field(description="退款金额（单位：元）")
    reason: str = Field(description="退款原因")


class NetworkStatusInput(BaseModel):
    """Input schema for checking network status."""

    location: str | None = Field(
        default=None, description="可选，所在城市或地区名称，用于给出更贴近的网络状态描述"
    )


class BillingQueryTool(BaseTool):
    """LangChain tool that queries user's realtime balance."""

    name = "query_realtime_balance"
    description = "查询用户当前话费/余额情况"
    args_schema: Type[BaseModel] = BillingQueryInput

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
            balance = billing_service.query_realtime_balance(db, user_id_int)
        finally:
            db.close()

        if balance is None:
            return "未找到该用户，无法查询余额。"

        return f"用户 {user_id_int} 当前预估余额约为 {balance:.2f} 元。"

    async def _arun(self, user_id: str) -> str:  # pragma: no cover - sync only
        raise NotImplementedError("BillingQueryTool 暂不支持异步调用。")


class ProcessRefundTool(BaseTool):
    """LangChain tool that processes a refund for the user."""

    name = "process_refund"
    description = "为用户发起退款申请"
    args_schema: Type[BaseModel] = RefundInput

    def __init__(self, db_session_factory: sessionmaker, **kwargs):
        super().__init__(**kwargs)
        self._db_session_factory = db_session_factory

    def _run(self, user_id: str, amount: float, reason: str) -> str:
        try:
            user_id_int = int(user_id)
        except ValueError:
            return "无效的用户ID，请提供数字格式的用户ID。"

        if amount <= 0:
            return "退款金额必须大于 0 元。"

        db: Session = self._db_session_factory()
        try:
            result = billing_service.process_refund(db, user_id_int, amount, reason)
        finally:
            db.close()

        if result is None:
            return "退款申请失败，可能是用户不存在或金额不合法。"

        return (
            f"已为用户 {user_id_int} 提交 {amount:.2f} 元的退款申请，"
            f"原因：{reason}。当前状态：{result['status']}。"
        )

    async def _arun(self, user_id: str, amount: float, reason: str) -> str:  # pragma: no cover
        raise NotImplementedError("ProcessRefundTool 暂不支持异步调用。")


class CheckNetworkStatusTool(BaseTool):
    """LangChain tool that returns a human-friendly description of network status."""

    name = "check_network_status"
    description = "查询当前网络状态，用于安抚用户或排查问题前的说明"
    args_schema: Type[BaseModel] = NetworkStatusInput

    def _run(self, location: str | None = None) -> str:
        # 在真实环境中，这里可以接入网络监控系统或告警平台。
        prefix = f"当前{location}地区" if location else "当前你所在地区"
        return (
            f"{prefix}的整体网络运行正常，暂未发现大面积故障。如果你仍然感觉网络异常，"
            "可以尝试重启手机、切换飞行模式，或向我描述更具体的场景，我会继续帮你排查。"
        )

    async def _arun(self, location: str | None = None) -> str:  # pragma: no cover
        raise NotImplementedError("CheckNetworkStatusTool 暂不支持异步调用。")

