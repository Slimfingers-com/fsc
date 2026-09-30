from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.agency_provenance import detect_agency_provenance
from app.enums.source_dependency import ArticleProvenanceKind
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.source import SourceRepository
from app.repositories.source_dependency import SourceDependencyRepository


@dataclass(frozen=True, slots=True)
class AgencyProvenanceBackfillReport:
    scanned_articles: int
    detected_candidates: int
    change_count: int
    already_present: int
    missing_upstream_source: int
    self_dependencies_skipped: int
    changes_by_source: dict[str, int]


class AgencyProvenanceBackfiller:
    def __init__(
        self,
        *,
        source_repository: SourceRepository | None = None,
        dependency_repository: SourceDependencyRepository | None = None,
    ) -> None:
        self.source_repository = source_repository or SourceRepository()
        self.dependency_repository = (
            dependency_repository or SourceDependencyRepository()
        )

    def backfill(self, db: Session) -> AgencyProvenanceBackfillReport:
        rows = db.execute(
            select(Article, Feed.source_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
            .where(
                Article.deleted_at.is_(None),
                Article.author.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
            .order_by(Article.id)
        ).all()

        source_cache: dict[str, Source | None] = {}
        changes_by_source: Counter[str] = Counter()
        detected = 0
        changed = 0
        missing = 0
        self_skipped = 0

        for article, article_source_id in rows:
            candidate = detect_agency_provenance(
                author=article.author,
                provider=None,
            )
            if candidate is None:
                continue

            detected += 1
            if candidate.source_slug not in source_cache:
                source_cache[candidate.source_slug] = (
                    self.source_repository.get_by_slug(
                        db,
                        candidate.source_slug,
                    )
                )
            upstream_source = source_cache[candidate.source_slug]
            if upstream_source is None or not upstream_source.active:
                missing += 1
                continue
            if upstream_source.id == article_source_id:
                self_skipped += 1
                continue
            inserted = (
                self.dependency_repository
                .add_unverified_article_provenance_candidate(
                    db,
                    article_id=article.id,
                    upstream_source_id=upstream_source.id,
                    relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
                    confidence=candidate.confidence,
                    detection_method=candidate.detection_method,
                    notes=(
                        "Historical agency provenance candidate backfilled "
                        f"from {candidate.detection_method.value}: "
                        f"{candidate.evidence}"
                    ),
                )
            )
            if inserted:
                changed += 1
                changes_by_source[upstream_source.slug] += 1

        already_present = (
            detected - changed - missing - self_skipped
        )
        return AgencyProvenanceBackfillReport(
            scanned_articles=len(rows),
            detected_candidates=detected,
            change_count=changed,
            already_present=already_present,
            missing_upstream_source=missing,
            self_dependencies_skipped=self_skipped,
            changes_by_source=dict(sorted(changes_by_source.items())),
        )
