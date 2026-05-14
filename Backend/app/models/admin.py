from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Admin(Base):
    __tablename__ = "admin"

    admin_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_name: Mapped[str] = mapped_column(String(100), nullable=False)
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_initial_change: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    approved_swap_requests: Mapped[list["SwapRequest"]] = relationship(
        back_populates="approver",
    )
