from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums.story_pipeline import StoryPipeline
from app.models.coverage import (
    StoryCoverageGap,
    StoryCoverageSummary,
    StoryMissingPerspective,
)
from app.models.story_processing import StoryProcessingRun
from app.schemas.story_analysis import (
    StoryAnalysisClaimGroupRead,
    StoryAnalysisConsensusRead,
    StoryAnalysisCoverageGapRead,
    StoryAnalysisCoverageRead,
    StoryAnalysisDifferenceRead,
    StoryAnalysisEvidenceRead,
    StoryAnalysisGenerationRead,
    StoryAnalysisMemberRead,
    StoryAnalysisMissingPerspectiveRead,
    StoryAnalysisRead,
)
from app.services.coverage import (
    CoverageService,
    CoverageSnapshot,
)


class StoryAnalysisService:
    def __init__(
        self,
        coverage_service: CoverageService,
    ) -> None:
        self.coverage_service = coverage_service

    def _load_current_coverage(
        self,
        db: Session,
        *,
        snapshot: CoverageSnapshot,
    ) -> tuple[
        StoryCoverageSummary,
        list[StoryCoverageGap],
        list[StoryMissingPerspective],
    ] | None:
        story_id = (
            snapshot
            .consensus_snapshot
            .story.id
        )
        summary = db.scalar(
            select(
                StoryCoverageSummary
            ).where(
                StoryCoverageSummary.story_id
                == story_id,
                StoryCoverageSummary.deleted_at
                .is_(None),
            )
        )
        if summary is None:
            return None

        if (
            summary.consensus_processing_run_id
            != snapshot.consensus_processing_run_id
        ):
            return None

        run = db.get(
            StoryProcessingRun,
            summary.processing_run_id,
        )
        current_hash = (
            self.coverage_service
            .analysis_hash(snapshot)
        )
        if (
            run is None
            or run.story_id != story_id
            or run.pipeline
            != StoryPipeline.COVERAGE_ANALYSIS.value
            or run.outcome != "succeeded"
            or run.finished_at is None
            or run.input_hash != current_hash
            or run.provider
            != self.coverage_service.analyzer.provider
            or run.provider_version
            != self.coverage_service.analyzer.version
            or run.configuration_version
            != self.coverage_service
            .processing_configuration_version
        ):
            return None

        gaps = list(
            db.scalars(
                select(
                    StoryCoverageGap
                )
                .where(
                    StoryCoverageGap.story_id
                    == story_id,
                    StoryCoverageGap.deleted_at
                    .is_(None),
                )
                .order_by(
                    StoryCoverageGap.gap_kind,
                    StoryCoverageGap.id,
                )
            ).all()
        )
        missing = list(
            db.scalars(
                select(
                    StoryMissingPerspective
                )
                .where(
                    StoryMissingPerspective.story_id
                    == story_id,
                    StoryMissingPerspective.deleted_at
                    .is_(None),
                )
                .order_by(
                    StoryMissingPerspective
                    .claim_group_id,
                    StoryMissingPerspective.id,
                )
            ).all()
        )

        if any(
            item.processing_run_id
            != summary.processing_run_id
            for item in [
                *gaps,
                *missing,
            ]
        ):
            return None

        return (
            summary,
            gaps,
            missing,
        )

    @staticmethod
    def _generation_ids(
        snapshot: CoverageSnapshot,
        coverage: StoryCoverageSummary,
    ) -> StoryAnalysisGenerationRead | None:
        group_run_ids = {
            row.group.processing_run_id
            for row
            in snapshot.consensus_snapshot.rows
        } | {
            relation.processing_run_id
            for relation
            in snapshot
            .consensus_snapshot
            .relations
        }
        if len(group_run_ids) != 1:
            return None

        claim_relations_run_id = next(
            iter(group_run_ids)
        )
        member_run_ids = {
            row.member.processing_run_id
            for row
            in snapshot.consensus_snapshot.rows
        }
        if member_run_ids != {
            claim_relations_run_id
        }:
            return None

        evidence_run_ids = {
            evidence.processing_run_id
            for _, evidence
            in snapshot
            .consensus_snapshot
            .evidence
        } | {
            link.processing_run_id
            for link, _
            in snapshot
            .consensus_snapshot
            .evidence
        }
        if len(evidence_run_ids) != 1:
            return None

        return StoryAnalysisGenerationRead(
            claim_relations_run_id=(
                claim_relations_run_id
            ),
            evidence_run_id=next(
                iter(evidence_run_ids)
            ),
            consensus_run_id=(
                snapshot
                .consensus_processing_run_id
            ),
            coverage_run_id=(
                coverage.processing_run_id
            ),
        )

    def load(
        self,
        db: Session,
        *,
        story_id: UUID,
    ) -> StoryAnalysisRead | None:
        snapshot = (
            self.coverage_service
            .load_snapshot(
                db,
                story_id=story_id,
            )
        )
        if snapshot is None:
            return None

        initial_input_hash = (
            self.coverage_service
            .analysis_hash(snapshot)
        )

        current = self._load_current_coverage(
            db,
            snapshot=snapshot,
        )
        if current is None:
            return None
        coverage, gaps, missing = current

        generations = self._generation_ids(
            snapshot,
            coverage,
        )
        if generations is None:
            return None

        rows_by_group = {}
        for row in (
            snapshot
            .consensus_snapshot
            .rows
        ):
            rows_by_group.setdefault(
                row.group.id,
                [],
            ).append(row)

        consensus_by_group = {
            item.claim_group_id: item
            for item
            in snapshot.consensus_summaries
        }
        if (
            set(rows_by_group)
            != set(consensus_by_group)
        ):
            return None

        missing_by_group = {
            item.claim_group_id: item
            for item in missing
        }
        if not set(
            missing_by_group
        ).issubset(
            rows_by_group
        ):
            return None

        source_by_id = {
            row.source.id: row.source
            for row in snapshot.source_rows
        }
        evidence_by_group = {}
        for link, evidence in (
            snapshot
            .consensus_snapshot
            .evidence
        ):
            source = source_by_id.get(
                evidence.source_id
            )
            if source is None:
                return None
            evidence_by_group.setdefault(
                link.claim_group_id,
                [],
            ).append(
                StoryAnalysisEvidenceRead(
                    id=evidence.id,
                    claim_id=evidence.claim_id,
                    article_id=evidence.article_id,
                    source_id=evidence.source_id,
                    source_name=source.name,
                    source_slug=source.slug,
                    evidence_kind=(
                        evidence.evidence_kind
                    ),
                    relation_kind=(
                        link.relation_kind
                    ),
                    evidence_text=(
                        evidence.evidence_text
                    ),
                    evidence_confidence=(
                        evidence.confidence
                    ),
                    relation_confidence=(
                        link.confidence
                    ),
                )
            )

        claim_groups = []
        representative_text_by_group = {}
        for group_id in sorted(
            rows_by_group,
            key=str,
        ):
            rows = rows_by_group[
                group_id
            ]
            group = rows[0].group
            representative = next(
                (
                    row.claim
                    for row in rows
                    if row.claim.id
                    == group
                    .representative_claim_id
                ),
                None,
            )
            if representative is None:
                return None
            representative_text_by_group[
                group_id
            ] = representative.claim_text

            consensus = (
                consensus_by_group[
                    group_id
                ]
            )
            missing_item = (
                missing_by_group.get(
                    group_id
                )
            )
            members = [
                StoryAnalysisMemberRead(
                    claim_id=row.claim.id,
                    claim_text=(
                        row.claim.claim_text
                    ),
                    article_id=(
                        row.article.id
                    ),
                    article_title=(
                        row.article.title
                    ),
                    article_url=(
                        row.article.link
                    ),
                    published_at=(
                        row.article
                        .published_at
                    ),
                    source_id=(
                        row.source.id
                    ),
                    source_name=(
                        row.source.name
                    ),
                    source_slug=(
                        row.source.slug
                    ),
                    similarity_score=(
                        row.member
                        .similarity_score
                    ),
                    match_kind=(
                        row.member.match_kind
                    ),
                )
                for row in rows
            ]

            claim_groups.append(
                StoryAnalysisClaimGroupRead(
                    id=group.id,
                    representative_claim_id=(
                        group
                        .representative_claim_id
                    ),
                    representative_claim_text=(
                        representative.claim_text
                    ),
                    confidence=(
                        group.confidence
                    ),
                    members=members,
                    evidence=sorted(
                        evidence_by_group.get(
                            group_id,
                            [],
                        ),
                        key=lambda item: (
                            str(
                                item.source_id
                            ),
                            str(item.id),
                        ),
                    ),
                    consensus=(
                        StoryAnalysisConsensusRead(
                            consensus_kind=(
                                consensus
                                .consensus_kind
                            ),
                            claim_count=(
                                consensus
                                .claim_count
                            ),
                            article_count=(
                                consensus
                                .article_count
                            ),
                            independent_source_count=(
                                consensus
                                .independent_source_count
                            ),
                            evidence_item_count=(
                                consensus
                                .evidence_item_count
                            ),
                            evidence_source_count=(
                                consensus
                                .evidence_source_count
                            ),
                            attributed_perspective_count=(
                                consensus
                                .attributed_perspective_count
                            ),
                        )
                    ),
                    missing_perspective=(
                        StoryAnalysisMissingPerspectiveRead(
                            missing_kind=(
                                missing_item
                                .missing_kind
                            ),
                            contradiction_relation_ids=(
                                missing_item
                                .contradiction_relation_ids
                            ),
                        )
                        if missing_item
                        is not None
                        else None
                    ),
                )
            )

        relation_by_id = {
            relation.id: relation
            for relation
            in snapshot
            .consensus_snapshot
            .relations
        }
        differences = []
        for item in (
            snapshot.difference_summaries
        ):
            relation = relation_by_id.get(
                item.claim_relation_id
            )
            if relation is None:
                return None
            left_text = (
                representative_text_by_group
                .get(item.left_group_id)
            )
            right_text = (
                representative_text_by_group
                .get(item.right_group_id)
            )
            if (
                left_text is None
                or right_text is None
            ):
                return None
            differences.append(
                StoryAnalysisDifferenceRead(
                    id=item.id,
                    claim_relation_id=(
                        item.claim_relation_id
                    ),
                    left_group_id=(
                        item.left_group_id
                    ),
                    right_group_id=(
                        item.right_group_id
                    ),
                    left_claim_text=(
                        left_text
                    ),
                    right_claim_text=(
                        right_text
                    ),
                    difference_kind=(
                        item.difference_kind
                    ),
                    left_independent_source_count=(
                        item
                        .left_independent_source_count
                    ),
                    right_independent_source_count=(
                        item
                        .right_independent_source_count
                    ),
                    left_evidence_source_count=(
                        item
                        .left_evidence_source_count
                    ),
                    right_evidence_source_count=(
                        item
                        .right_evidence_source_count
                    ),
                )
            )

        story = (
            snapshot
            .consensus_snapshot
            .story
        )
        response = StoryAnalysisRead(
            story_id=story.id,
            language_code=(
                story.language_code
            ),
            generations=generations,
            claim_groups=claim_groups,
            differences=sorted(
                differences,
                key=lambda item: (
                    str(
                        item.claim_relation_id
                    )
                ),
            ),
            coverage=(
                StoryAnalysisCoverageRead(
                    article_count=(
                        coverage.article_count
                    ),
                    source_count=(
                        coverage.source_count
                    ),
                    content_source_count=(
                        coverage
                        .content_source_count
                    ),
                    signal_source_count=(
                        coverage
                        .signal_source_count
                    ),
                    independent_content_source_count=(
                        coverage
                        .independent_content_source_count
                    ),
                    claim_group_count=(
                        coverage
                        .claim_group_count
                    ),
                    shared_group_count=(
                        coverage
                        .shared_group_count
                    ),
                    difference_count=(
                        coverage
                        .difference_count
                    ),
                    attributed_group_count=(
                        coverage
                        .attributed_group_count
                    ),
                    source_type_counts=(
                        coverage
                        .source_type_counts
                    ),
                    coverage_scope_counts=(
                        coverage
                        .coverage_scope_counts
                    ),
                    country_counts=(
                        coverage.country_counts
                    ),
                )
            ),
            coverage_gaps=[
                StoryAnalysisCoverageGapRead(
                    id=item.id,
                    gap_kind=item.gap_kind,
                    observed_count=(
                        item.observed_count
                    ),
                    minimum_expected=(
                        item.minimum_expected
                    ),
                )
                for item in gaps
            ],
        )

        # Force a true READ COMMITTED re-read rather than
        # reusing stale ORM instances from SQLAlchemy's identity map.
        db.expire_all()

        fresh_snapshot = (
            self.coverage_service
            .load_snapshot(
                db,
                story_id=story_id,
            )
        )
        if fresh_snapshot is None:
            return None
        if (
            self.coverage_service
            .analysis_hash(
                fresh_snapshot
            )
            != initial_input_hash
        ):
            return None

        fresh_current = (
            self._load_current_coverage(
                db,
                snapshot=fresh_snapshot,
            )
        )
        if fresh_current is None:
            return None
        fresh_coverage, _, _ = (
            fresh_current
        )
        fresh_generations = (
            self._generation_ids(
                fresh_snapshot,
                fresh_coverage,
            )
        )
        if (
            fresh_generations is None
            or fresh_generations
            != generations
            or fresh_coverage.id
            != coverage.id
        ):
            return None

        return response
