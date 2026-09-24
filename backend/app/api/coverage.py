from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from app.core.settings import settings
from app.coverage.provider import (
    CoverageGapKind,
    MissingPerspectiveKind,
)
from app.db.session import get_db
from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.claim_relation import (
    StoryClaimGroup,
    StoryClaimGroupMember,
)
from app.models.consensus import StoryConsensusSummary
from app.models.coverage import (
    StoryCoverageGap,
    StoryCoverageSummary,
    StoryMissingPerspective,
)
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.schemas.coverage import (
    CoverageGapPageRead,
    CoverageGapRead,
    CoverageSummaryRead,
    MissingPerspectivePageRead,
    MissingPerspectiveRead,
)


router = APIRouter(tags=["coverage"])


def _story_exists(
    db: Session,
    story_id: UUID,
) -> bool:
    return (
        db.scalar(
            select(Story.id).where(
                Story.id == story_id,
                Story.deleted_at.is_(None),
            )
        )
        is not None
    )


def _current_coverage_condition():
    current_consensus = exists(
        select(
            StoryConsensusSummary.id
        ).where(
            StoryConsensusSummary.story_id
            == StoryCoverageSummary.story_id,
            StoryConsensusSummary.processing_run_id
            == StoryCoverageSummary
            .consensus_processing_run_id,
            StoryConsensusSummary.deleted_at.is_(None),
        )
    )
    other_consensus_generation = exists(
        select(
            StoryConsensusSummary.id
        ).where(
            StoryConsensusSummary.story_id
            == StoryCoverageSummary.story_id,
            StoryConsensusSummary.processing_run_id
            != StoryCoverageSummary
            .consensus_processing_run_id,
            StoryConsensusSummary.deleted_at.is_(None),
        )
    )
    return (
        StoryCoverageSummary.deleted_at.is_(None)
        & current_consensus
        & ~other_consensus_generation
    )


def _eligible_group(
    group_alias,
):
    member = aliased(
        StoryClaimGroupMember
    )
    claim = aliased(ArticleClaim)
    article = aliased(Article)
    feed = aliased(Feed)
    source = aliased(Source)
    membership = aliased(StoryArticle)

    active_representative = exists(
        select(ArticleClaim.id)
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
                StoryArticle.story_id
                == group_alias.story_id
            )
            & (
                StoryArticle.article_id
                == Article.id
            ),
        )
        .where(
            ArticleClaim.id
            == group_alias
            .representative_claim_id,
            ArticleClaim.deleted_at.is_(None),
            Article.deleted_at.is_(None),
            Article.normalized_at.is_not(None),
            Article.normalized_text.is_not(None),
            StoryArticle.deleted_at.is_(None),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
        )
    )

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
            (
                membership.story_id
                == group_alias.story_id
            )
            & (
                membership.article_id
                == article.id
            )
            & (
                membership.deleted_at.is_(
                    None
                )
            ),
        )
        .where(
            member.group_id
            == group_alias.id,
            member.deleted_at.is_(None),
            (
                (
                    claim.deleted_at
                    .is_not(None)
                )
                | (
                    article.deleted_at
                    .is_not(None)
                )
                | (
                    article.normalized_at
                    .is_(None)
                )
                | (
                    article.normalized_text
                    .is_(None)
                )
                | (
                    feed.deleted_at
                    .is_not(None)
                )
                | (
                    feed.active
                    .is_(False)
                )
                | (
                    source.deleted_at
                    .is_not(None)
                )
                | (
                    source.active
                    .is_(False)
                )
                | (
                    membership.id
                    .is_(None)
                )
            ),
        )
    )
    return (
        active_representative
        & ~ineligible_member
    )


def _current_summary_statement(
    story_id: UUID,
):
    return select(
        StoryCoverageSummary
    ).where(
        StoryCoverageSummary.story_id
        == story_id,
        _current_coverage_condition(),
    )


@router.get(
    "/stories/{story_id}/coverage",
    response_model=CoverageSummaryRead,
)
def story_coverage(
    story_id: UUID,
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

    summary = db.scalar(
        _current_summary_statement(
            story_id
        )
    )
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Coverage not found.",
        )

    return CoverageSummaryRead(
        id=summary.id,
        story_id=summary.story_id,
        article_count=(
            summary.article_count
        ),
        source_count=(
            summary.source_count
        ),
        content_source_count=(
            summary.content_source_count
        ),
        signal_source_count=(
            summary.signal_source_count
        ),
        independent_content_source_count=(
            summary
            .independent_content_source_count
        ),
        claim_group_count=(
            summary.claim_group_count
        ),
        shared_group_count=(
            summary.shared_group_count
        ),
        difference_count=(
            summary.difference_count
        ),
        attributed_group_count=(
            summary.attributed_group_count
        ),
        source_type_counts=(
            summary.source_type_counts
        ),
        coverage_scope_counts=(
            summary.coverage_scope_counts
        ),
        country_counts=(
            summary.country_counts
        ),
        analysis_provider=(
            summary.analysis_provider
        ),
        analysis_version=(
            summary.analysis_version
        ),
        analyzed_at=(
            summary.analyzed_at
        ),
    )


@router.get(
    "/stories/{story_id}/coverage-gaps",
    response_model=CoverageGapPageRead,
)
def story_coverage_gaps(
    story_id: UUID,
    gap_kind: CoverageGapKind | None = None,
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

    statement = (
        select(StoryCoverageGap)
        .join(
            StoryCoverageSummary,
            (
                StoryCoverageSummary
                .story_id
                == StoryCoverageGap
                .story_id
            )
            & (
                StoryCoverageSummary
                .processing_run_id
                == StoryCoverageGap
                .processing_run_id
            ),
        )
        .where(
            StoryCoverageGap.story_id
            == story_id,
            StoryCoverageGap.deleted_at.is_(None),
            _current_coverage_condition(),
        )
    )
    if gap_kind is not None:
        statement = statement.where(
            StoryCoverageGap.gap_kind
            == gap_kind
        )

    size = min(
        page_size
        or settings.coverage_default_page_size,
        settings.coverage_max_page_size,
    )
    total = (
        db.scalar(
            select(func.count())
            .select_from(
                statement
                .order_by(None)
                .subquery()
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            statement
            .order_by(
                StoryCoverageGap.gap_kind,
                StoryCoverageGap.id,
            )
            .offset(
                (page - 1) * size
            )
            .limit(size)
        ).all()
    )
    return CoverageGapPageRead(
        items=[
            CoverageGapRead(
                id=item.id,
                story_id=item.story_id,
                gap_kind=item.gap_kind,
                observed_count=(
                    item.observed_count
                ),
                minimum_expected=(
                    item.minimum_expected
                ),
                analysis_provider=(
                    item.analysis_provider
                ),
                analysis_version=(
                    item.analysis_version
                ),
                analyzed_at=(
                    item.analyzed_at
                ),
            )
            for item in rows
        ],
        total=total,
        page=page,
        page_size=size,
        pages=(
            ceil(total / size)
            if total
            else 0
        ),
    )


@router.get(
    "/stories/{story_id}/missing-perspectives",
    response_model=MissingPerspectivePageRead,
)
def story_missing_perspectives(
    story_id: UUID,
    missing_kind: (
        MissingPerspectiveKind | None
    ) = None,
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

    representative = aliased(
        ArticleClaim
    )
    statement = (
        select(
            StoryMissingPerspective,
            representative.claim_text
            .label(
                "representative_claim_text"
            ),
        )
        .join(
            StoryCoverageSummary,
            (
                StoryCoverageSummary
                .story_id
                == StoryMissingPerspective
                .story_id
            )
            & (
                StoryCoverageSummary
                .processing_run_id
                == StoryMissingPerspective
                .processing_run_id
            ),
        )
        .join(
            StoryClaimGroup,
            StoryClaimGroup.id
            == StoryMissingPerspective
            .claim_group_id,
        )
        .join(
            representative,
            representative.id
            == StoryClaimGroup
            .representative_claim_id,
        )
        .where(
            StoryMissingPerspective.story_id
            == story_id,
            StoryMissingPerspective.deleted_at.is_(None),
            StoryClaimGroup.deleted_at.is_(None),
            representative.deleted_at.is_(None),
            _current_coverage_condition(),
            _eligible_group(
                StoryClaimGroup
            ),
        )
    )
    if missing_kind is not None:
        statement = statement.where(
            StoryMissingPerspective
            .missing_kind
            == missing_kind
        )

    size = min(
        page_size
        or settings.coverage_default_page_size,
        settings.coverage_max_page_size,
    )
    total = (
        db.scalar(
            select(func.count())
            .select_from(
                statement
                .order_by(None)
                .subquery()
            )
        )
        or 0
    )
    rows = db.execute(
        statement
        .order_by(
            StoryMissingPerspective
            .claim_group_id
        )
        .offset(
            (page - 1) * size
        )
        .limit(size)
    ).all()

    return MissingPerspectivePageRead(
        items=[
            MissingPerspectiveRead(
                id=row[0].id,
                story_id=row[0].story_id,
                claim_group_id=(
                    row[0].claim_group_id
                ),
                representative_claim_text=(
                    row
                    .representative_claim_text
                ),
                missing_kind=(
                    row[0].missing_kind
                ),
                contradiction_relation_ids=(
                    row[0]
                    .contradiction_relation_ids
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
            ceil(total / size)
            if total
            else 0
        ),
    )
