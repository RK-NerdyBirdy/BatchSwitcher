from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SwapRequest(Base):
    __tablename__ = "swap_request"
    __table_args__ = (
        sa.CheckConstraint(
            "requester_assignment_id <> target_assignment_id",
            name="ck_swap_request_different_assignments",
        ),
        sa.Index(
            "uq_swap_request_active_pair",
            sa.text("LEAST(requester_assignment_id, target_assignment_id)"),
            sa.text("GREATEST(requester_assignment_id, target_assignment_id)"),
            unique=True,
            postgresql_where=sa.text("status IN ('PENDING','ACCEPTED')"),
        ),
    )

    request_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requester_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("student_semester_assignment.assignment_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("student_semester_assignment.assignment_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("admin.admin_id"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    requester_assignment: Mapped["StudentSemesterAssignment"] = relationship(
        back_populates="swap_requests_requested",
        foreign_keys=[requester_assignment_id],
    )
    target_assignment: Mapped["StudentSemesterAssignment"] = relationship(
        back_populates="swap_requests_targeted",
        foreign_keys=[target_assignment_id],
    )
    approver: Mapped["Admin"] = relationship(back_populates="approved_swap_requests")
    history: Mapped["SwapHistory"] = relationship(
        back_populates="request",
        uselist=False,
    )
