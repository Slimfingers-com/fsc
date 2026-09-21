from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.evidence.provider import EvidenceKind, EvidenceRelationKind
from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.claim_relation import StoryClaimGroup
from app.models.evidence import StoryClaimEvidence, StoryEvidence
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.schemas.evidence import EvidencePageRead, EvidenceRead


router = APIRouter(tags=["evidence"])


def _story_exists(db: Session, story_id: UUID) -> bool:
    return (
        db.scalar(
            select(Story.id)
            .where(
                Story.id == story_id,
                Story.deleted_at.is_(None),
            )
        )
        is not None
    )


def _base_statement(story_id: UUID):
    return (
        select(
            StoryEvidence,
            StoryClaimEvidence,
            ArticleClaim.claim_text.label("claim_text"),
            Article.title.label("article_title"),
            Article.link.label("article_url"),
            Article.published_at.label("published_at"),
            Source.name.label("source_name"),
            Source.slug.label("source_slug"),
        )
        .join(
            StoryClaimEvidence,
            StoryClaimEvidence.evidence_id == StoryEvidence.id,
        )
        .join(
            StoryClaimGroup,
            StoryClaimGroup.id == StoryClaimEvidence.claim_group_id,
        )
        .join(
            ArticleClaim,
            ArticleClaim.id == StoryEvidence.claim_id,
        )
        .join(
            Article,
            Article.id == StoryEvidence.article_id,
        )
        .join(Feed, Feed.id == Article.feed_id)
        .join(Source, Source.id == Feed.source_id)
        .join(
            StoryArticle,
            (StoryArticle.story_id == story_id)
            & (StoryArticle.article_id == Article.id),
        )
        .where(
            StoryEvidence.story_id == story_id,
            StoryEvidence.deleted_at.is_(None),
            StoryClaimEvidence.deleted_at.is_(None),
            StoryClaimGroup.deleted_at.is_(None),
            ArticleClaim.deleted_at.is_(None),
            Article.deleted_at.is_(None),
            Article.normalized_at.is_not(None),
            Article.normalized_text.is_not(None),
            StoryArticle.deleted_at.is_(None),
            StoryEvidence.source_id == Source.id,
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
        )
    )


def _read(row) -> EvidenceRead:
    evidence = row[0]
    link = row[1]
    return EvidenceRead(
        id=evidence.id,
        story_id=evidence.story_id,
        claim_group_id=link.claim_group_id,
        claim_id=evidence.claim_id,
        claim_text=row.claim_text,
        article_id=evidence.article_id,
        article_title=row.article_title,
        article_url=row.article_url,
        published_at=row.published_at,
        source_id=evidence.source_id,
        source_name=row.source_name,
        source_slug=row.source_slug,
        evidence_kind=evidence.evidence_kind,
        relation_kind=link.relation_kind,
        evidence_text=evidence.evidence_text,
        evidence_confidence=evidence.confidence,
        relation_confidence=link.confidence,
        analysis_provider=evidence.analysis_provider,
        analysis_version=evidence.analysis_version,
        analyzed_at=evidence.analyzed_at,
    )


def _page(
    db: Session,
    statement,
    *,
    page: int,
    page_size: int | None,
) -> EvidencePageRead:
    size = min(
        page_size or settings.evidence_default_page_size,
        settings.evidence_max_page_size,
    )
    total = (
        db.scalar(
            select(func.count()).select_from(
                statement.order_by(None).subquery()
            )
        )
        or 0
    )
    rows = db.execute(
        statement.order_by(
            StoryClaimEvidence.claim_group_id,
            StoryEvidence.evidence_kind,
            Source.slug,
            Article.published_at.desc().nullslast(),
            StoryEvidence.id,
        )
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return EvidencePageRead(
        items=[_read(row) for row in rows],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size) if total else 0,
    )


@router.get(
    "/stories/{story_id}/evidence",
    response_model=EvidencePageRead,
)
def story_evidence(
    story_id: UUID,
    evidence_kind: EvidenceKind | None = None,
    relation_kind: EvidenceRelationKind | None = None,
    source_id: UUID | None = None,
    min_confidence: Annotated[
        float,
        Query(ge=0, le=1),
    ] = 0.0,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
):
    if not _story_exists(db, story_id):
        raise HTTPException(
            status_code=404,
            detail="Story not found.",
        )

    statement = _base_statement(story_id).where(
        StoryEvidence.confidence >= min_confidence,
        StoryClaimEvidence.confidence >= min_confidence,
    )
    if evidence_kind is not None:
        statement = statement.where(
            StoryEvidence.evidence_kind == evidence_kind
        )
    if relation_kind is not None:
        statement = statement.where(
            StoryClaimEvidence.relation_kind == relation_kind
        )
    if source_id is not None:
        statement = statement.where(
            StoryEvidence.source_id == source_id
        )

    return _page(
        db,
        statement,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/claim-groups/{group_id}/evidence",
    response_model=EvidencePageRead,
)
def claim_group_evidence(
    group_id: UUID,
    evidence_kind: EvidenceKind | None = None,
    relation_kind: EvidenceRelationKind | None = None,
    min_confidence: Annotated[
        float,
        Query(ge=0, le=1),
    ] = 0.0,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
):
    group = db.scalar(
        select(StoryClaimGroup).where(
            StoryClaimGroup.id == group_id,
            StoryClaimGroup.deleted_at.is_(None),
        )
    )
    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Claim group not found.",
        )

    statement = _base_statement(group.story_id).where(
        StoryClaimEvidence.claim_group_id == group_id,
        StoryEvidence.confidence >= min_confidence,
        StoryClaimEvidence.confidence >= min_confidence,
    )
    if evidence_kind is not None:
        statement = statement.where(
            StoryEvidence.evidence_kind == evidence_kind
        )
    if relation_kind is not None:
        statement = statement.where(
            StoryClaimEvidence.relation_kind == relation_kind
        )

    return _page(
        db,
        statement,
        page=page,
        page_size=page_size,
    )
