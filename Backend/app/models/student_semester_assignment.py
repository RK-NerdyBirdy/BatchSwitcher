from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StudentSemesterAssignment(Base):
    __tablename__ = "student_semester_assignment"
    __table_args__ = (
        sa.UniqueConstraint(
            "register_number",
            "semester_id",
            name="uq_assignment_register_semester",
        ),
        sa.CheckConstraint("cgpa >= 0 AND cgpa <= 10", name="ck_assignment_cgpa_range"),
    )

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    register_number: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("student.register_number", ondelete="CASCADE"),
        nullable=False,
    )
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semester.semester_id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batch.batch_id", ondelete="CASCADE"),
        nullable=False,
    )
    cgpa: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    student: Mapped["Student"] = relationship(back_populates="assignments")
    semester: Mapped["Semester"] = relationship(back_populates="assignments")
    batch: Mapped["Batch"] = relationship(back_populates="assignments")
    swap_requests_requested: Mapped[list["SwapRequest"]] = relationship(
        back_populates="requester_assignment",
        foreign_keys="SwapRequest.requester_assignment_id",
        cascade="all, delete-orphan",
    )
    swap_requests_targeted: Mapped[list["SwapRequest"]] = relationship(
        back_populates="target_assignment",
        foreign_keys="SwapRequest.target_assignment_id",
        cascade="all, delete-orphan",
    )
