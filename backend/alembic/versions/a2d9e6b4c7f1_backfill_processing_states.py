"""backfill processing states

Revision ID: a2d9e6b4c7f1
Revises: f1c8d5a7b2e4
"""

import hashlib
import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, insert


revision: str = "a2d9e6b4c7f1"
down_revision: str | None = "f1c8d5a7b2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


article_processing_states = sa.table(
    "article_processing_states",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("article_id", UUID(as_uuid=True)),
    sa.column("pipeline", sa.String()),
    sa.column("processed_input_hash", sa.String()),
    sa.column("processed_provider", sa.String()),
    sa.column("processed_provider_version", sa.String()),
    sa.column("processed_configuration_version", sa.String()),
    sa.column("last_processed_at", sa.DateTime(timezone=True)),
    sa.column("attempt_count", sa.Integer()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
    sa.column("deleted_at", sa.DateTime(timezone=True)),
)

articles = sa.table(
    "articles",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("title", sa.Text()),
    sa.column("summary", sa.Text()),
    sa.column("content", sa.Text()),
    sa.column("normalization_version", sa.Integer()),
    sa.column("normalized_at", sa.DateTime(timezone=True)),
    sa.column("deleted_at", sa.DateTime(timezone=True)),
)

search_documents = sa.table(
    "search_documents",
    sa.column("article_id", UUID(as_uuid=True)),
    sa.column("document_hash", sa.String()),
    sa.column("builder_version", sa.Integer()),
    sa.column("indexed_at", sa.DateTime(timezone=True)),
    sa.column("deleted_at", sa.DateTime(timezone=True)),
)


def _normalization_input_hash(
    title: str | None,
    summary: str | None,
    content: str | None,
) -> str:
    payload = [
        title or "",
        summary or "",
        content or "",
    ]

    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _insert_state(
    connection,
    *,
    article_id,
    pipeline: str,
    input_hash: str,
    provider: str,
    provider_version: str,
    configuration_version: str,
    processed_at,
) -> None:
    statement = (
        insert(article_processing_states)
        .values(
            article_id=article_id,
            pipeline=pipeline,
            processed_input_hash=input_hash,
            processed_provider=provider,
            processed_provider_version=provider_version,
            processed_configuration_version=configuration_version,
            last_processed_at=processed_at,
            attempt_count=0,
        )
        .on_conflict_do_nothing(
            index_elements=[
                article_processing_states.c.article_id,
                article_processing_states.c.pipeline,
            ],
            index_where=(
                article_processing_states.c.deleted_at.is_(None)
            ),
        )
    )

    connection.execute(statement)


def upgrade() -> None:
    connection = op.get_bind()

    normalized_rows = connection.execute(
        sa.select(
            articles.c.id,
            articles.c.title,
            articles.c.summary,
            articles.c.content,
            articles.c.normalized_at,
        ).where(
            articles.c.deleted_at.is_(None),
            articles.c.normalized_at.is_not(None),
            articles.c.normalization_version == 1,
        )
    )

    for row in normalized_rows:
        _insert_state(
            connection,
            article_id=row.id,
            pipeline="normalization",
            input_hash=_normalization_input_hash(
                row.title,
                row.summary,
                row.content,
            ),
            provider="content_normalizer",
            provider_version="1",
            configuration_version="1",
            processed_at=row.normalized_at,
        )

    indexed_rows = connection.execute(
        sa.select(
            search_documents.c.article_id,
            search_documents.c.document_hash,
            search_documents.c.builder_version,
            search_documents.c.indexed_at,
        ).where(
            search_documents.c.deleted_at.is_(None),
            search_documents.c.builder_version == 1,
        )
    )

    for row in indexed_rows:
        _insert_state(
            connection,
            article_id=row.article_id,
            pipeline="search_indexing",
            input_hash=row.document_hash,
            provider="search_document_builder",
            provider_version=str(row.builder_version),
            configuration_version="1",
            processed_at=row.indexed_at,
        )


def downgrade() -> None:
    pass
