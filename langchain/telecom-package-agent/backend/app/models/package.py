from __future__ import annotations

from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Package(TimestampMixin, Base):
    __tablename__ = "package"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_fee: Mapped[float] = mapped_column(Float, nullable=False)
    data_quota_gb: Mapped[float] = mapped_column(Float, nullable=False)
    validity_days: Mapped[int] = mapped_column(nullable=False, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user_packages: Mapped[list["UserPackage"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )
    benefits: Mapped[list["Benefit"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_package_name", "name"),
        Index("ix_package_is_active", "is_active"),
    )


