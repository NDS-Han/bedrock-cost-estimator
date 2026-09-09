from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ModelPriceRecord(Base):
    __tablename__ = "model_prices"

    model_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255))
    family: Mapped[str] = mapped_column(String(16), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    input_cost_per_token: Mapped[Decimal] = mapped_column(Numeric(24, 16))
    output_cost_per_token: Mapped[Decimal] = mapped_column(Numeric(24, 16))
    cache_read_cost_per_token: Mapped[Decimal] = mapped_column(Numeric(24, 16))
    cache_write_cost_per_token: Mapped[Decimal] = mapped_column(Numeric(24, 16))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceSyncRun(Base):
    __tablename__ = "price_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    stored_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
