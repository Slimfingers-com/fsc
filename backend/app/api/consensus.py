from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from app.consensus.provider import ConsensusKind, DifferenceKind
from app.core.settings import settings
from app.db.session import get_db
from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.claim_relation import StoryClaimGroup, StoryClaimGroupMember
from app.models.consensus import (
    StoryConsensusSummary,
    StoryDifferenceSummary,
)
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.schemas.consensus import (
    ConsensusPageRead,
    ConsensusRead,
    DifferencePageRead,
    DifferenceRead,
)


router = APIRouter(tags=["consensus"])


def _eligible_group(group_alias):
    representative = aliased(ArticleClaim)
    article = aliased(Article)
    feed = aliased(Feed)
    source = aliased(Source)
    membership = aliased(StoryArticle)

    return exists(
        select(representative.id)
        .join(
            article,
            article.id == representative.article_id,
        )
        .join(feed, feed.id == article.feed_id)
        .join(source, source.id == feed.source_id)
        .join(
            membership,
            (membership.story_id == group_alias.story_id)
            & (membership.article_id == article.id),
        )
        .where(
            representative.id
            == group_alias.representative_claim_id,
            representative.deleted_at.is_(None),
            membership.deleted_at.is_(None),
            article.deleted_at.is_(None),
            article.normalized_at.is_not(None),
            article.normalized_text.is_not(None),
            feed.deleted_at.is_(None),
            feed.active.is_(True),
            source.deleted_at.is_(None),
            source.active.is_(True),
        )
    )


def _fully_eligible_group(group_alias):
    member = aliased(StoryClaimGroupMember)
    claim = aliased(ArticleClaim)
    article = aliased(Article)
    feed = aliased(Feed)
    source = aliased(Source)
    membership = aliased(StoryArticle)

    ineligible_member = exists(
        select(member.id)
        .join(
            claim,
            claim.id == member.claim_id,
        )
        .join(
            article,
            article.id == claim.article_id,
        )
        .join(
            feed,
            feed.id == article.feed_id,
        )
        .join(
            source,
            source.id == feed.source_id,
        )
        .outerjoin(
            membership,
            (membership.story_id == group_alias.story_id)
            & (membership.article_id == article.id)
            & (membership.deleted_at.is_(None)),
        )
        .where(
            member.group_id == group_alias.id,
            member.deleted_at.is_(None),
            (
                (claim.deleted_at.is_not(None))
                | (article.deleted_at.is_not(None))
                | (article.normalized_at.is_(None))
                | (article.normalized_text.is_(None))
                | (feed.deleted_at.is_not(None))
                | (feed.active.is_(False))
                | (source.deleted_at.is_not(None))
                | (source.active.is_(False))
                | (membership.id.is_(None))
            ),
        )
    )
    return (
        _eligible_group(group_alias)
        & ~ineligible_member
    )


def _story_exists(db: Session, story_id: UUID) -> bool:
    return (
        db.scalar(
            select(Story.id).where(
                Story.id == story_id,
                Story.deleted_at.is_(None),
            )
        )
        is not None
    )


@router.get(
    "/stories/{story_id}/consensus",
    response_model=ConsensusPageRead,
)
def story_consensus(
    story_id: UUID,
    consensus_kind: ConsensusKind | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
):
    if not _story_exists(db, story_id):
        raise HTTPException(status_code=404, detail="Story not found.")

    representative = aliased(ArticleClaim)
    statement = (
        select(
            StoryConsensusSummary,
            StoryClaimGroup.representative_claim_id,
            representative.claim_text.label("representative_claim_text"),
        )
        .join(
            StoryClaimGroup,
            StoryClaimGroup.id == StoryConsensusSummary.claim_group_id,
        )
        .join(
            representative,
            representative.id == StoryClaimGroup.representative_claim_id,
        )
        .where(
            StoryConsensusSummary.story_id == story_id,
            StoryConsensusSummary.deleted_at.is_(None),
            StoryClaimGroup.deleted_at.is_(None),
            representative.deleted_at.is_(None),
            _fully_eligible_group(StoryClaimGroup),
        )
    )
    if consensus_kind is not None:
        statement = statement.where(
            StoryConsensusSummary.consensus_kind == consensus_kind
        )

    size = min(
        page_size or settings.consensus_default_page_size,
        settings.consensus_max_page_size,
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
            StoryConsensusSummary.consensus_kind,
            StoryConsensusSummary.independent_source_count.desc(),
            StoryConsensusSummary.claim_group_id,
        )
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    return ConsensusPageRead(
        items=[
            ConsensusRead(
                id=row[0].id,
                story_id=row[0].story_id,
                claim_group_id=row[0].claim_group_id,
                representative_claim_id=row.representative_claim_id,
                representative_claim_text=row.representative_claim_text,
                consensus_kind=row[0].consensus_kind,
                claim_count=row[0].claim_count,
                article_count=row[0].article_count,
                independent_source_count=row[0].independent_source_count,
                evidence_item_count=row[0].evidence_item_count,
                evidence_source_count=row[0].evidence_source_count,
                attributed_perspective_count=row[0].attributed_perspective_count,
                analysis_provider=row[0].analysis_provider,
                analysis_version=row[0].analysis_version,
                analyzed_at=row[0].analyzed_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size) if total else 0,
    )


@router.get(
    "/stories/{story_id}/differences",
    response_model=DifferencePageRead,
)
def story_differences(
    story_id: UUID,
    difference_kind: DifferenceKind | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
):
    if not _story_exists(db, story_id):
        raise HTTPException(status_code=404, detail="Story not found.")

    left = aliased(StoryClaimGroup)
    right = aliased(StoryClaimGroup)
    left_claim = aliased(ArticleClaim)
    right_claim = aliased(ArticleClaim)

    statement = (
        select(
            StoryDifferenceSummary,
            left_claim.claim_text.label("left_claim_text"),
            right_claim.claim_text.label("right_claim_text"),
        )
        .join(left, left.id == StoryDifferenceSummary.left_group_id)
        .join(right, right.id == StoryDifferenceSummary.right_group_id)
        .join(left_claim, left_claim.id == left.representative_claim_id)
        .join(right_claim, right_claim.id == right.representative_claim_id)
        .where(
            StoryDifferenceSummary.story_id == story_id,
            StoryDifferenceSummary.deleted_at.is_(None),
            left.deleted_at.is_(None),
            right.deleted_at.is_(None),
            left_claim.deleted_at.is_(None),
            right_claim.deleted_at.is_(None),
            _fully_eligible_group(left),
            _fully_eligible_group(right),
        )
    )
    if difference_kind is not None:
        statement = statement.where(
            StoryDifferenceSummary.difference_kind == difference_kind
        )

    size = min(
        page_size or settings.consensus_default_page_size,
        settings.consensus_max_page_size,
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
            StoryDifferenceSummary.claim_relation_id
        )
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    return DifferencePageRead(
        items=[
            DifferenceRead(
                id=row[0].id,
                story_id=row[0].story_id,
                claim_relation_id=row[0].claim_relation_id,
                left_group_id=row[0].left_group_id,
                right_group_id=row[0].right_group_id,
                left_claim_text=row.left_claim_text,
                right_claim_text=row.right_claim_text,
                difference_kind=row[0].difference_kind,
                left_independent_source_count=row[0].left_independent_source_count,
                right_independent_source_count=row[0].right_independent_source_count,
                left_evidence_source_count=row[0].left_evidence_source_count,
                right_evidence_source_count=row[0].right_evidence_source_count,
                analysis_provider=row[0].analysis_provider,
                analysis_version=row[0].analysis_version,
                analyzed_at=row[0].analyzed_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size) if total else 0,
    )
