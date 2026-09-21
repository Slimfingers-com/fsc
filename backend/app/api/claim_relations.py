from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, exists, func, select
from sqlalchemy.orm import Session, aliased

from app.claim_relations.provider import ClaimRelationKind
from app.core.settings import settings
from app.db.session import get_db
from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.claim_relation import (
    StoryClaimGroup,
    StoryClaimGroupMember,
    StoryClaimRelation,
)
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.schemas.claim_relation import (
    ClaimGroupDetailRead,
    ClaimGroupMemberRead,
    ClaimGroupPageRead,
    ClaimGroupSummaryRead,
    ClaimRelationPageRead,
    ClaimRelationRead,
)


router = APIRouter(tags=["claim-relations"])


def _story_exists(db: Session, story_id: UUID) -> bool:
    return (
        db.scalar(
            select(Story.id)
            .join(
                StoryArticle,
                StoryArticle.story_id == Story.id,
            )
            .join(
                Article,
                Article.id == StoryArticle.article_id,
            )
            .join(
                Feed,
                Feed.id == Article.feed_id,
            )
            .join(
                Source,
                Source.id == Feed.source_id,
            )
            .where(
                Story.id == story_id,
                Story.deleted_at.is_(None),
                StoryArticle.deleted_at.is_(None),
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
            .limit(1)
        )
        is not None
    )


def _group_summary_statement(story_id: UUID):
    representative = aliased(ArticleClaim)

    return (
        select(
            StoryClaimGroup,
            representative.claim_text.label(
                "representative_claim_text"
            ),
            func.count(
                StoryClaimGroupMember.id
            ).label("claim_count"),
            func.count(
                distinct(Article.id)
            ).label("article_count"),
            func.count(
                distinct(Source.id)
            ).label("source_count"),
        )
        .join(
            Story,
            Story.id
            == StoryClaimGroup.story_id,
        )
        .join(
            representative,
            representative.id
            == StoryClaimGroup.representative_claim_id,
        )
        .join(
            StoryClaimGroupMember,
            StoryClaimGroupMember.group_id
            == StoryClaimGroup.id,
        )
        .join(
            ArticleClaim,
            ArticleClaim.id
            == StoryClaimGroupMember.claim_id,
        )
        .join(
            Article,
            Article.id == ArticleClaim.article_id,
        )
        .join(
            Feed,
            Feed.id == Article.feed_id,
        )
        .join(
            Source,
            Source.id == Feed.source_id,
        )
        .join(
            StoryArticle,
            (
                StoryArticle.article_id
                == Article.id
            )
            & (
                StoryArticle.story_id
                == StoryClaimGroup.story_id
            ),
        )
        .where(
            StoryClaimGroup.story_id
            == story_id,
            Story.deleted_at.is_(
                None
            ),
            StoryClaimGroup.deleted_at.is_(
                None
            ),
            StoryClaimGroupMember.deleted_at.is_(
                None
            ),
            representative.deleted_at.is_(
                None
            ),
            ArticleClaim.deleted_at.is_(
                None
            ),
            StoryArticle.deleted_at.is_(
                None
            ),
            Article.deleted_at.is_(
                None
            ),
            Article.normalized_at.is_not(
                None
            ),
            Article.normalized_text.is_not(
                None
            ),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
        )
        .group_by(
            StoryClaimGroup.id,
            representative.claim_text,
        )
    )


def _summary(row) -> ClaimGroupSummaryRead:
    group = row[0]

    return ClaimGroupSummaryRead(
        id=group.id,
        story_id=group.story_id,
        representative_claim_id=(
            group.representative_claim_id
        ),
        representative_claim_text=(
            row.representative_claim_text
        ),
        claim_count=row.claim_count,
        article_count=row.article_count,
        source_count=row.source_count,
        confidence=group.confidence,
        analysis_provider=(
            group.analysis_provider
        ),
        analysis_version=(
            group.analysis_version
        ),
        analyzed_at=group.analyzed_at,
    )


@router.get(
    "/stories/{story_id}/claim-groups",
    response_model=ClaimGroupPageRead,
)
def story_claim_groups(
    story_id: UUID,
    min_sources: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    page: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    page_size: Annotated[
        int | None,
        Query(ge=1),
    ] = None,
    db: Session = Depends(get_db),
):
    if not _story_exists(
        db,
        story_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Story not found.",
        )

    size = min(
        page_size
        or settings.claim_relation_default_page_size,
        settings.claim_relation_max_page_size,
    )

    base = (
        _group_summary_statement(
            story_id
        )
        .having(
            func.count(
                distinct(Source.id)
            )
            >= min_sources
        )
    )

    count_statement = select(
        func.count()
    ).select_from(
        base.order_by(None).subquery()
    )
    total = (
        db.scalar(
            count_statement
        )
        or 0
    )

    rows = db.execute(
        base.order_by(
            func.count(
                distinct(Source.id)
            ).desc(),
            func.count(
                StoryClaimGroupMember.id
            ).desc(),
            StoryClaimGroup.group_hash,
            StoryClaimGroup.id,
        )
        .offset(
            (page - 1) * size
        )
        .limit(size)
    ).all()

    return ClaimGroupPageRead(
        items=[
            _summary(row)
            for row in rows
        ],
        total=total,
        page=page,
        page_size=size,
        pages=(
            ceil(
                total / size
            )
            if total
            else 0
        ),
    )


@router.get(
    "/claim-groups/{group_id}",
    response_model=ClaimGroupDetailRead,
)
def claim_group_detail(
    group_id: UUID,
    db: Session = Depends(get_db),
):
    group = db.get(
        StoryClaimGroup,
        group_id,
    )

    if (
        group is None
        or group.deleted_at
        is not None
    ):
        raise HTTPException(
            status_code=404,
            detail="Claim group not found.",
        )

    summary_row = (
        db.execute(
            _group_summary_statement(
                group.story_id
            ).where(
                StoryClaimGroup.id
                == group_id
            )
        )
        .one_or_none()
    )

    if summary_row is None:
        raise HTTPException(
            status_code=404,
            detail="Claim group not found.",
        )

    member_rows = db.execute(
        select(
            StoryClaimGroupMember,
            ArticleClaim.claim_text.label(
                "claim_text"
            ),
            Article.id.label(
                "article_id"
            ),
            Article.title.label(
                "article_title"
            ),
            Article.link.label(
                "article_url"
            ),
            Article.published_at.label(
                "published_at"
            ),
            Source.id.label(
                "source_id"
            ),
            Source.name.label(
                "source_name"
            ),
            Source.slug.label(
                "source_slug"
            ),
        )
        .join(
            ArticleClaim,
            ArticleClaim.id
            == StoryClaimGroupMember.claim_id,
        )
        .join(
            Article,
            Article.id
            == ArticleClaim.article_id,
        )
        .join(
            Feed,
            Feed.id == Article.feed_id,
        )
        .join(
            Source,
            Source.id == Feed.source_id,
        )
        .join(
            StoryArticle,
            (
                StoryArticle.article_id
                == Article.id
            )
            & (
                StoryArticle.story_id
                == group.story_id
            ),
        )
        .where(
            StoryClaimGroupMember.group_id
            == group_id,
            StoryClaimGroupMember.deleted_at.is_(
                None
            ),
            ArticleClaim.deleted_at.is_(
                None
            ),
            StoryArticle.deleted_at.is_(
                None
            ),
            Article.deleted_at.is_(
                None
            ),
            Article.normalized_at.is_not(
                None
            ),
            Article.normalized_text.is_not(
                None
            ),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
        )
        .order_by(
            Source.slug,
            Article.published_at.asc()
            .nullsfirst(),
            Article.id,
            ArticleClaim.id,
        )
    ).all()

    summary = _summary(
        summary_row
    )

    return ClaimGroupDetailRead(
        **summary.model_dump(),
        members=[
            ClaimGroupMemberRead(
                id=row[0].id,
                claim_id=row[0].claim_id,
                claim_text=(
                    row.claim_text
                ),
                article_id=(
                    row.article_id
                ),
                article_title=(
                    row.article_title
                ),
                article_url=(
                    row.article_url
                ),
                published_at=(
                    row.published_at
                ),
                source_id=(
                    row.source_id
                ),
                source_name=(
                    row.source_name
                ),
                source_slug=(
                    row.source_slug
                ),
                similarity_score=(
                    row[0].similarity_score
                ),
                match_kind=(
                    row[0].match_kind
                ),
            )
            for row in member_rows
        ],
    )


@router.get(
    "/stories/{story_id}/claim-relations",
    response_model=ClaimRelationPageRead,
)
def story_claim_relations(
    story_id: UUID,
    relation_kind: (
        ClaimRelationKind | None
    ) = None,
    min_confidence: Annotated[
        float,
        Query(ge=0, le=1),
    ] = 0.0,
    page: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    page_size: Annotated[
        int | None,
        Query(ge=1),
    ] = None,
    db: Session = Depends(get_db),
):
    if not _story_exists(
        db,
        story_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Story not found.",
        )

    size = min(
        page_size
        or settings.claim_relation_default_page_size,
        settings.claim_relation_max_page_size,
    )

    left = aliased(
        StoryClaimGroup
    )
    right = aliased(
        StoryClaimGroup
    )
    left_claim = aliased(
        ArticleClaim
    )
    right_claim = aliased(
        ArticleClaim
    )

    def eligible_representative(
        group_alias,
    ):
        return exists(
            select(ArticleClaim.id)
            .join(
                Article,
                Article.id
                == ArticleClaim.article_id,
            )
            .join(
                Feed,
                Feed.id
                == Article.feed_id,
            )
            .join(
                Source,
                Source.id
                == Feed.source_id,
            )
            .join(
                StoryArticle,
                (
                    StoryArticle.article_id
                    == Article.id
                )
                & (
                    StoryArticle.story_id
                    == story_id
                ),
            )
            .where(
                group_alias.story_id
                == story_id,
                ArticleClaim.id
                == group_alias.representative_claim_id,
                ArticleClaim.deleted_at.is_(
                    None
                ),
                StoryArticle.deleted_at.is_(
                    None
                ),
                Article.deleted_at.is_(
                    None
                ),
                Article.normalized_at.is_not(
                    None
                ),
                Article.normalized_text.is_not(
                    None
                ),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
        )

    conditions = [
        StoryClaimRelation.story_id
        == story_id,
        StoryClaimRelation.deleted_at.is_(
            None
        ),
        left.deleted_at.is_(None),
        right.deleted_at.is_(None),
        left_claim.deleted_at.is_(
            None
        ),
        right_claim.deleted_at.is_(
            None
        ),
        eligible_representative(
            left
        ),
        eligible_representative(
            right
        ),
        StoryClaimRelation.confidence
        >= min_confidence,
    ]

    if relation_kind is not None:
        conditions.append(
            StoryClaimRelation.relation_kind
            == relation_kind
        )

    total = (
        db.scalar(
            select(
                func.count(
                    StoryClaimRelation.id
                )
            )
            .select_from(
                StoryClaimRelation
            )
            .join(
                left,
                left.id
                == StoryClaimRelation.left_group_id,
            )
            .join(
                right,
                right.id
                == StoryClaimRelation.right_group_id,
            )
            .join(
                left_claim,
                left_claim.id
                == left.representative_claim_id,
            )
            .join(
                right_claim,
                right_claim.id
                == right.representative_claim_id,
            )
            .where(
                *conditions
            )
        )
        or 0
    )

    rows = db.execute(
        select(
            StoryClaimRelation,
            left_claim.claim_text.label(
                "left_claim_text"
            ),
            right_claim.claim_text.label(
                "right_claim_text"
            ),
        )
        .join(
            left,
            left.id
            == StoryClaimRelation.left_group_id,
        )
        .join(
            right,
            right.id
            == StoryClaimRelation.right_group_id,
        )
        .join(
            left_claim,
            left_claim.id
            == left.representative_claim_id,
        )
        .join(
            right_claim,
            right_claim.id
            == right.representative_claim_id,
        )
        .where(
            *conditions
        )
        .order_by(
            StoryClaimRelation.confidence.desc(),
            StoryClaimRelation.left_group_id,
            StoryClaimRelation.right_group_id,
            StoryClaimRelation.id,
        )
        .offset(
            (page - 1) * size
        )
        .limit(size)
    ).all()

    return ClaimRelationPageRead(
        items=[
            ClaimRelationRead(
                id=row[0].id,
                story_id=(
                    row[0].story_id
                ),
                left_group_id=(
                    row[0].left_group_id
                ),
                right_group_id=(
                    row[0].right_group_id
                ),
                left_claim_text=(
                    row.left_claim_text
                ),
                right_claim_text=(
                    row.right_claim_text
                ),
                relation_kind=(
                    row[0].relation_kind
                ),
                confidence=(
                    row[0].confidence
                ),
                analysis_provider=(
                    row[0].analysis_provider
                ),
                analysis_version=(
                    row[0].analysis_version
                ),
                analyzed_at=(
                    row[0].analyzed_at
                ),
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=size,
        pages=(
            ceil(
                total / size
            )
            if total
            else 0
        ),
    )
