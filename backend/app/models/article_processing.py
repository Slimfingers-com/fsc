from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseModel

if TYPE_CHECKING:
    from app.models.article import Article


class ArticleProcessingState(BaseModel):
    __tablename__ = "article_processing_states"

    __table_args__ = (
        Index(
            "uq_article_processing_states_active",
            "article_id",
            "pipeline",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_article_processing_states_attempt_count_nonnegative",
        ),
        CheckConstraint(
            """
            (
                claimed_at IS NULL
                AND claimed_by IS NULL
                AND claim_expires_at IS NULL
                AND claimed_input_hash IS NULL
                AND claimed_provider IS NULL
                AND claimed_provider_version IS NULL
                AND claimed_configuration_version IS NULL
            )
            OR
            (
                claimed_at IS NOT NULL
                AND claimed_by IS NOT NULL
                AND claim_expires_at IS NOT NULL
                AND claimed_input_hash IS NOT NULL
                AND claimed_provider IS NOT NULL
                AND claimed_provider_version IS NOT NULL
                AND claimed_configuration_version IS NOT NULL
            )
            """,
            name="ck_article_processing_states_claim_complete",
        ),
        CheckConstraint(
            "claim_expires_at IS NULL OR claim_expires_at > claimed_at",
            name="ck_article_processing_states_claim_expiry",
        ),
        CheckConstraint(
            """
            (
                last_processed_at IS NULL
                AND processed_input_hash IS NULL
                AND processed_provider IS NULL
                AND processed_provider_version IS NULL
                AND processed_configuration_version IS NULL
            )
            OR
            (
                last_processed_at IS NOT NULL
                AND processed_input_hash IS NOT NULL
                AND processed_provider IS NOT NULL
                AND processed_provider_version IS NOT NULL
                AND processed_configuration_version IS NOT NULL
            )
            """,
            name="ck_article_processing_states_processed_identity",
        ),
    )

    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    processed_input_hash: Mapped[str | None] = mapped_column(String(64))
    processed_provider: Mapped[str | None] = mapped_column(String(100))
    processed_provider_version: Mapped[str | None] = mapped_column(String(100))
    processed_configuration_version: Mapped[str | None] = mapped_column(String(100))
    last_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    claimed_input_hash: Mapped[str | None] = mapped_column(String(64))
    claimed_provider: Mapped[str | None] = mapped_column(String(100))
    claimed_provider_version: Mapped[str | None] = mapped_column(String(100))
    claimed_configuration_version: Mapped[str | None] = mapped_column(String(100))

    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(100), index=True)
    claim_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    retry_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_error_code: Mapped[str | None] = mapped_column(String(100))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    article: Mapped["Article"] = relationship(back_populates="processing_states")
    runs: Mapped[list["ArticleProcessingRun"]] = relationship(
        back_populates="processing_state"
    )


class ArticleProcessingRun(Base):
    __tablename__ = "article_processing_runs"

    __table_args__ = (
        CheckConstraint(
            "attempt_number > 0",
            name="ck_article_processing_runs_attempt_number_positive",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_article_processing_runs_finished_after_started",
        ),
        CheckConstraint(
            """
            outcome IS NULL
            OR outcome IN ('succeeded', 'failed', 'skipped', 'lease_lost')
            """,
            name="ck_article_processing_runs_outcome",
        ),
        CheckConstraint(
            """
            (finished_at IS NULL AND outcome IS NULL)
            OR
            (finished_at IS NOT NULL AND outcome IS NOT NULL)
            """,
            name="ck_article_processing_runs_completion_pair",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    processing_state_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("article_processing_states.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    pipeline: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)

    worker_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(50), index=True)

    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    article: Mapped["Article"] = relationship(back_populates="processing_runs")
    processing_state: Mapped["ArticleProcessingState | None"] = relationship(
        back_populates="runs"
    )