from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.consensus.rule_based import (
    RuleBasedConsensusAnalyzer,
)
from app.core.settings import settings
from app.coverage.rule_based import (
    RuleBasedCoverageAnalyzer,
)
from app.db.session import get_db
from app.models.story import Story, StoryArticle
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.models.coverage import StoryCoverageSummary
from app.models.story_processing import StoryProcessingRun
from app.enums.story_pipeline import StoryPipeline
from app.schemas.story_analysis import (
    StoryAnalysisRead,
    ReadyAnalysisSummaryRead,
)
from app.services.consensus import ConsensusService
from app.services.coverage import CoverageService
from app.services.story_analysis import (
    StoryAnalysisService,
)


router = APIRouter(tags=["story-analysis"])


service = StoryAnalysisService(
    CoverageService(
        analyzer=RuleBasedCoverageAnalyzer(
            minimum_independent_content_sources=(
                settings
                .coverage_minimum_independent_content_sources
            )
        ),
        consensus_service=ConsensusService(
            analyzer=RuleBasedConsensusAnalyzer(
                minimum_independent_sources=(
                    settings
                    .consensus_minimum_independent_sources
                )
            )
        ),
    )
)


@router.get(
    "/stories/{story_id}/analysis",
    response_model=StoryAnalysisRead,
)
def story_analysis(
    story_id: UUID,
    db: Session = Depends(get_db),
):
    story_exists = (
        db.scalar(
            select(Story.id).where(
                Story.id == story_id,
                Story.deleted_at.is_(None),
            )
        )
        is not None
    )
    if not story_exists:
        raise HTTPException(
            status_code=404,
            detail="Story not found.",
        )

    result = service.load(
        db,
        story_id=story_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Current story analysis "
                "is not available."
            ),
        )
    return result


@router.get(
    "/analyses/ready",
    response_model=list[ReadyAnalysisSummaryRead],
)
def ready_analyses(
    limit: Annotated[int, Query(ge=1, le=8)] = 6,
    db: Session = Depends(get_db),
):
    """Discover finished, *current* analyses visible to German readers.

    The inexpensive coverage index only supplies candidate IDs; each card
    still passes the complete StoryAnalysisService generation/hash checks.
    Never label an outdated cached coverage summary as a ready analysis.
    Bound candidate checks on the small production host.
    """
    candidates = list(
        db.scalars(
            select(StoryCoverageSummary.story_id)
            .join(
                StoryProcessingRun,
                StoryProcessingRun.id == StoryCoverageSummary.processing_run_id,
            )
            .where(
                StoryCoverageSummary.deleted_at.is_(None),
                StoryProcessingRun.pipeline
                == StoryPipeline.COVERAGE_ANALYSIS.value,
                StoryProcessingRun.outcome == "succeeded",
                StoryProcessingRun.finished_at.is_not(None),
            )
            .order_by(
                StoryCoverageSummary.analyzed_at.desc(),
                StoryCoverageSummary.story_id,
            )
            .limit(max(16, limit * 4))
        ).all()
    )

    if not candidates:
        return []

    # Reuse the same active, normalized-article eligibility rules as the
    # public Story reader. One bounded query covers every recent candidate,
    # rather than loading an entire Story and its entities/topics repeatedly.
    # Only German wording is exposed; publisher country is not restricted.
    language = func.lower(func.trim(Article.language_code))
    german_rows = db.execute(
        select(
            StoryArticle.story_id,
            Article.title,
            StoryArticle.article_time,
            Source.id.label("source_id"),
        )
        .select_from(StoryArticle)
        .join(Story, Story.id == StoryArticle.story_id)
        .join(Article, Article.id == StoryArticle.article_id)
        .join(Feed, Feed.id == Article.feed_id)
        .join(Source, Source.id == Feed.source_id)
        .where(
            StoryArticle.story_id.in_(candidates),
            StoryArticle.deleted_at.is_(None),
            Story.deleted_at.is_(None),
            Article.deleted_at.is_(None),
            Article.normalized_at.is_not(None),
            Article.normalized_text.is_not(None),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
            or_(language == "de", language.like("de-%")),
        )
        .order_by(
            StoryArticle.story_id,
            StoryArticle.article_time.desc(),
            StoryArticle.id.desc(),
        )
    ).all()

    visible_by_story = {}
    for row in german_rows:
        info = visible_by_story.setdefault(
            row.story_id,
            {
                "article_count": 0,
                "source_ids": set(),
                "title": None,
                "last_article_at": row.article_time,
            },
        )
        info["article_count"] += 1
        info["source_ids"].add(row.source_id)
        if info["title"] is None and row.title and row.title.strip():
            info["title"] = row.title.strip()
        if row.article_time > info["last_article_at"]:
            info["last_article_at"] = row.article_time

    ready: list[ReadyAnalysisSummaryRead] = []
    for story_id in candidates:
        visible = visible_by_story.get(story_id)
        if (
            visible is None
            or len(visible["source_ids"]) < 2
            or visible["title"] is None
        ):
            # Do not pay for full generation/hash validation on events that
            # cannot be shown to the German public in the first place.
            continue
        try:
            if service.load(db, story_id=story_id) is None:
                continue
            ready.append(
                ReadyAnalysisSummaryRead(
                    story_id=story_id,
                    title=visible["title"],
                    source_count=len(visible["source_ids"]),
                    article_count=visible["article_count"],
                    last_article_at=visible["last_article_at"],
                )
            )
            if len(ready) >= limit:
                break
        finally:
            # Keep bounded ORM memory growth without rolling back the
            # transactional view used by test fixtures.
            db.expire_all()
    return ready
