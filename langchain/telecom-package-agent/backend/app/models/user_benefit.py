from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class UserBenefit(TimestampMixin, Base):
    __tablename__ = "user_benefit"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    benefit_id: Mapped[int] = mapped_column(
        ForeignKey("benefit.id", ondelete="CASCADE"), index=True
    )

    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")

    user: Mapped["User"] = relationship(back_populates="user_benefits")
    benefit: Mapped["Benefit"] = relationship(back_populates="user_benefits")

    __table_args__ = (
        Index("ix_user_benefit_user_id_benefit_id", "user_id", "benefit_id"),
        Index("ix_user_benefit_status", "status"),
    )


