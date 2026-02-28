from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class UsageRecord(TimestampMixin, Base):
    __tablename__ = "usage_record"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    package_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("package.id", ondelete="SET NULL"), index=True, nullable=True
    )

    used_mb: Mapped[float] = mapped_column(Float, nullable=False)
    record_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    network_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship(back_populates="usage_records")
    package: Mapped[Optional["Package"]] = relationship(back_populates="usage_records")

    __table_args__ = (
        Index("ix_usage_record_user_id_record_time", "user_id", "record_time"),
    )


