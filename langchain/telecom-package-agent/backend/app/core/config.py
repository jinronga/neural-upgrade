from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

# 确保从 backend 或项目根目录都能加载 .env
_backend_dir = Path(__file__).resolve().parent.parent.parent
for _env_path in (_backend_dir / ".env", _backend_dir.parent / ".env"):
    if _env_path.exists():
        load_dotenv(_env_path)
        break
else:
    load_dotenv()


def _read_optional_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    APP_NAME: str = os.getenv("APP_NAME", "telecom-package-agent")
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://root:password@localhost:3306/telecom_package_agent?charset=utf8mb4",
    )

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # 只支持一个配置项：OPENAI_BASE_URL。未配置或配置为空字符串时视为 None。
    OPENAI_BASE_URL: Optional[str] = _read_optional_env("OPENAI_BASE_URL")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    def get_openai_client_kwargs(self) -> dict[str, str]:
        """构建 ChatOpenAI 的通用参数，便于统一接入 OpenAI 兼容服务。"""
        kwargs: dict[str, str] = {}
        if self.OPENAI_API_KEY:
            kwargs["openai_api_key"] = self.OPENAI_API_KEY
        if self.OPENAI_BASE_URL:
            kwargs["base_url"] = self.OPENAI_BASE_URL.rstrip("/")
        return kwargs


settings = Settings()
