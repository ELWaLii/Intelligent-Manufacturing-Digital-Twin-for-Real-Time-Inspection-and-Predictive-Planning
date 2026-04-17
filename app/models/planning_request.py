from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanningRequest(Base):
    __tablename__ = "planning_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    available_workers: Mapped[int] = mapped_column(Integer, nullable=False)
    available_raw_material: Mapped[float | None] = mapped_column(Float, nullable=True)
    shift_hours: Mapped[float] = mapped_column(Float, nullable=False)
    planning_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
