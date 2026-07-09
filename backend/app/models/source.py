from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    url: Mapped[str] = mapped_column(Text, nullable=False)
    rss_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    coverage_scope: Mapped[str | None] = mapped_column(String(50), nullable=True)

    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    ownership: Mapped[str | None] = mapped_column(Text, nullable=True)
    funding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    paywall: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    transparency_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correction_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_source_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    priority_tier: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
