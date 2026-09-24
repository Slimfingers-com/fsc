from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
    SourceRelationKind,
)

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.source import Source


class SourceRelation(BaseModel):
    __tablename__ = "source_relations"

    __table_args__ = (
        Index(
            "uq_source_relations_active_identity",
            "source_id",
            "related_source_id",
            "relation_kind",
            "valid_from",
            "valid_to",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "source_id <> related_source_id",
            name="ck_source_relation_distinct_sources",
        ),
        CheckConstraint(
            "relation_kind IN ("
            "'editorial_parent', 'shared_newsroom', 'content_supplier', "
            "'syndication_partner', 'joint_editorial_operation'"
            ")",
            name="ck_source_relation_kind",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_source_relation_valid_range",
        ),
        Index(
            "ix_source_relations_source_kind",
            "source_id",
            "relation_kind",
        ),
        Index(
            "ix_source_relations_related_kind",
            "related_source_id",
            "relation_kind",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    related_source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_kind: Mapped[SourceRelationKind] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    provenance_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source"] = relationship(
        foreign_keys=[source_id],
        back_populates="outgoing_relations",
    )
    related_source: Mapped["Source"] = relationship(
        foreign_keys=[related_source_id],
        back_populates="incoming_relations",
    )


class ArticleProvenance(BaseModel):
    __tablename__ = "article_provenance"

    __table_args__ = (
        Index(
            "uq_article_provenance_active_identity",
            "article_id",
            "upstream_source_id",
            "upstream_article_id",
            "relation_kind",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "upstream_article_id IS NULL OR article_id <> upstream_article_id",
            name="ck_article_provenance_distinct_articles",
        ),
        CheckConstraint(
            "relation_kind IN ("
            "'supplied_by', 'syndicated_from', 'republished_from', "
            "'co_produced_with'"
            ")",
            name="ck_article_provenance_kind",
        ),
        CheckConstraint(
            "detection_method IN ("
            "'manual', 'feed_metadata', 'provider_metadata', "
            "'canonical_url', 'byline', 'content_similarity', 'other'"
            ")",
            name="ck_article_provenance_detection_method",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_article_provenance_confidence_range",
        ),
        Index(
            "ix_article_provenance_article_verified",
            "article_id",
            "verified",
        ),
        Index(
            "ix_article_provenance_upstream_source_verified",
            "upstream_source_id",
            "verified",
        ),
    )

    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upstream_source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    upstream_article_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relation_kind: Mapped[ArticleProvenanceKind] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default=text("1.0"),
    )
    detection_method: Mapped[ArticleProvenanceDetectionMethod] = mapped_column(
        String(40),
        nullable=False,
        default=ArticleProvenanceDetectionMethod.MANUAL,
        server_default=text("'manual'"),
        index=True,
    )
    verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    provenance_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    article: Mapped["Article"] = relationship(
        foreign_keys=[article_id],
        back_populates="provenance",
    )
    upstream_source: Mapped["Source"] = relationship(
        foreign_keys=[upstream_source_id],
        back_populates="article_provenance_as_upstream",
    )
    upstream_article: Mapped["Article | None"] = relationship(
        foreign_keys=[upstream_article_id],
    )
