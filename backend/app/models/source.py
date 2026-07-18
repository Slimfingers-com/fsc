from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.enums.coverage_scope import CoverageScope
from app.enums.source_type import SourceType

if TYPE_CHECKING:
    from app.models.feed import Feed

class Source(BaseModel):
    __tablename__ = "sources"

    __table_args__ = (
        CheckConstraint(
            "transparency_level BETWEEN 0 AND 100",
            name="ck_sources_transparency_level_range",
        ),
        CheckConstraint(
            "primary_source_usage BETWEEN 0 AND 100",
            name="ck_sources_primary_source_usage_range",
        ),
        CheckConstraint(
            "priority_tier BETWEEN 1 AND 4",
            name="ck_sources_priority_tier_range",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    api_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"),
        nullable=False,
    )

    coverage_scope: Mapped[CoverageScope | None] = mapped_column(
        Enum(CoverageScope, name="coverage_scope"),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    ownership: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    funding_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    paywall: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    transparency_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    correction_policy: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    primary_source_usage: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    priority_tier: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default=text("3"),
    )

    feeds: Mapped[list["Feed"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )
