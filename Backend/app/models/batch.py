from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Batch(Base):
    __tablename__ = "batch"

    batch_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_name: Mapped[str] = mapped_column(String(50), nullable=False)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semester.semester_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    semester: Mapped["Semester"] = relationship(back_populates="batches")
    assignments: Mapped[list["StudentSemesterAssignment"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )
