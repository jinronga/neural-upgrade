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


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    APP_NAME: str = os.getenv("APP_NAME", "telecom-package-agent")
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://root:password@localhost:3306/telecom_package_agent?charset=utf8mb4",
    )

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


settings = Settings()

