from __future__ import annotations

from typing import List, Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.services import package_service


class RecommendPackageInput(BaseModel):
    """Input schema for recommending packages."""

    user_id: str = Field(description="用户ID")
    monthly_budget: Optional[float] = Field(
        default=None, description="用户可接受的每月资费上限（单位：元）"
    )
    min_data_gb: Optional[float] = Field(
        default=None, description="期望的每月最小流量（单位：GB）"
    )


class RecommendPackageTool(BaseTool):
    """LangChain tool that recommends telecom packages for a user."""

    name: str = "recommend_package"
    description: str = "根据用户历史用量和预算，推荐合适的流量套餐"
    args_schema: Type[BaseModel] = RecommendPackageInput

    def __init__(self, db_session_factory: sessionmaker, **kwargs):
        super().__init__(**kwargs)
        self._db_session_factory = db_session_factory

    def _run(
        self, user_id: str, monthly_budget: Optional[float] = None, min_data_gb: Optional[float] = None
    ) -> str:
        try:
            user_id_int = int(user_id)
        except ValueError:
            return "无效的用户ID，请提供数字格式的用户ID。"

        usage_data = {
            "avg_monthly_used_gb": min_data_gb,
            "max_monthly_budget": monthly_budget,
        }

        db: Session = self._db_session_factory()
        try:
            packages = package_service.recommend_package(
                db, user_id=user_id_int, usage_data=usage_data
            )
        finally:
            db.close()

        if not packages:
            return "暂时没有找到符合条件的推荐套餐，请尝试放宽预算或流量要求。"

        lines: List[str] = ["为你推荐以下套餐："]
        for pkg in packages:
            lines.append(
                f"- {pkg.name}：月费 {pkg.monthly_fee:.2f} 元，包含 {pkg.data_quota_gb:.2f} GB 流量，有效期 {pkg.validity_days} 天。"
            )

        return "\n".join(lines)

    async def _arun(
        self, user_id: str, monthly_budget: Optional[float] = None, min_data_gb: Optional[float] = None
    ) -> str:  # pragma: no cover - sync only
        raise NotImplementedError("RecommendPackageTool 暂不支持异步调用。")

