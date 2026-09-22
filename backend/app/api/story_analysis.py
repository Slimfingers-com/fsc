from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.consensus.rule_based import (
    RuleBasedConsensusAnalyzer,
)
from app.core.settings import settings
from app.coverage.rule_based import (
    RuleBasedCoverageAnalyzer,
)
from app.db.session import get_db
from app.models.story import Story
from app.schemas.story_analysis import (
    StoryAnalysisRead,
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
