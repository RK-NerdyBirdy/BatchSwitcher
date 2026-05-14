from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SwapHistory(Base):
    __tablename__ = "swap_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("swap_request.request_id", ondelete="CASCADE"),
        nullable=False,
    )
    requester_old_batch: Mapped[int] = mapped_column(
        ForeignKey("batch.batch_id"),
        nullable=False,
    )
    requester_new_batch: Mapped[int] = mapped_column(
        ForeignKey("batch.batch_id"),
        nullable=False,
    )
    target_old_batch: Mapped[int] = mapped_column(ForeignKey("batch.batch_id"), nullable=False)
    target_new_batch: Mapped[int] = mapped_column(ForeignKey("batch.batch_id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    request: Mapped["SwapRequest"] = relationship(back_populates="history")
