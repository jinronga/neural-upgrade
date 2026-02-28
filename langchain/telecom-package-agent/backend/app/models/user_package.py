from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class UserPackage(TimestampMixin, Base):
    __tablename__ = "user_package"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    package_id: Mapped[int] = mapped_column(
        ForeignKey("package.id", ondelete="CASCADE"), index=True
    )

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="user_packages")
    package: Mapped["Package"] = relationship(back_populates="user_packages")

    __table_args__ = (
        Index("ix_user_package_user_id_package_id", "user_id", "package_id"),
        Index("ix_user_package_status", "status"),
    )


