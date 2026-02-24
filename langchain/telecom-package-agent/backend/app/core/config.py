from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel


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

