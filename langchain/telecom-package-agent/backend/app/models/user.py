from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    registered_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user_packages: Mapped[list["UserPackage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    user_benefits: Mapped[list["UserBenefit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    complaints: Mapped[list["Complaint"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_user_phone_number", "phone_number", unique=True),
        Index("ix_user_email", "email"),
    )


