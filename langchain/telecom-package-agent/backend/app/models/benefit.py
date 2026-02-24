from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Benefit(TimestampMixin, Base):
    __tablename__ = "benefit"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    inventory: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    package_id: Mapped[int | None] = mapped_column(
        ForeignKey("package.id", ondelete="SET NULL"), nullable=True
    )

    package: Mapped["Package | None"] = relationship(back_populates="benefits")
    user_benefits: Mapped[list["UserBenefit"]] = relationship(
        back_populates="benefit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_benefit_name", "name"),
        Index("ix_benefit_is_active", "is_active"),
    )


