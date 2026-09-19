import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clustering.features import (
    TITLE_FEATURE_VERSION,
    extract_title_terms,
)
from app.clustering.provider import (
    StoryCandidate,
    StoryClusterer,
    StoryClusteringInput,
    StoryClusteringResult,
)
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
)
from app.repositories.story import StoryRepository


@dataclass(frozen=True, slots=True)
class PreparedStoryClustering:
    article_title: str | None
    article: StoryClusteringInput
    candidates: tuple[StoryCandidate, ...]


@dataclass(frozen=True, slots=True)
class AppliedStoryClustering:
    story_id: UUID
    membership_id: UUID
    changed: bool
    match_kind: str


class StoryClusteringService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        *,
        clusterer: StoryClusterer,
        repository: StoryRepository | None = None,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        if not config_version:
            raise ValueError(
                "config_version must not be empty"
            )

        self.clusterer = clusterer
        self.repository = repository or StoryRepository()
        self.config_version = config_version

    def processing_configuration_version(
        self,
        *,
        window_hours: float,
        candidate_limit: int,
    ) -> str:
        if window_hours <= 0:
            raise ValueError(
                "window_hours must be greater than zero"
            )

        if candidate_limit <= 0:
            raise ValueError(
                "candidate_limit must be greater than zero"
            )

        payload = {
            "service_config_version": self.config_version,
            "title_feature_version": TITLE_FEATURE_VERSION,
            "clusterer_configuration": (
                self.clusterer.configuration()
            ),
            "window_hours": window_hours,
            "candidate_limit": candidate_limit,
        }

        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()

    def clustering_hash(
        self,
        article: Article,
        *,
        entity_ids: tuple[UUID, ...],
        topic_ids: tuple[UUID, ...],
    ) -> str:
        feature_title = (
            article.normalized_title
            or article.title
        )

        article_time = (
            article.published_at
            or article.created_at
        )

        payload = {
            "article_title": article.title or "",
            "article_time": article_time.isoformat(),
            "language_code": article.language_code or "",
            "title_feature_version": TITLE_FEATURE_VERSION,
            "title_terms": list(
                extract_title_terms(
                    feature_title
                )
            ),
            "entity_ids": [
                str(value)
                for value in sorted(
                    entity_ids,
                    key=str,
                )
            ],
            "topic_ids": [
                str(value)
                for value in sorted(
                    topic_ids,
                    key=str,
                )
            ],
        }

        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()

    def candidate(
        self,
        article: Article,
        *,
        entity_ids: tuple[UUID, ...],
        topic_ids: tuple[UUID, ...],
        window_hours: float,
        candidate_limit: int,
    ) -> ArticleProcessingCandidate:
        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=self.clustering_hash(
                article,
                entity_ids=entity_ids,
                topic_ids=topic_ids,
            ),
            provider=self.clusterer.provider,
            provider_version=self.clusterer.version,
            configuration_version=(
                self.processing_configuration_version(
                    window_hours=window_hours,
                    candidate_limit=candidate_limit,
                )
            ),
        )

    def prepare(
        self,
        db: Session,
        *,
        article_id: UUID,
        window_hours: float,
        candidate_limit: int,
    ) -> PreparedStoryClustering | None:
        article = db.scalar(
            select(Article)
            .join(
                Feed,
                Feed.id == Article.feed_id,
            )
            .join(
                Source,
                Source.id == Feed.source_id,
            )
            .where(
                Article.id == article_id,
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
        )

        if article is None:
            return None

        entity_ids_by_article, topic_ids_by_article = (
            self.repository.load_feature_ids(
                db,
                [article.id],
            )
        )

        feature_title = (
            article.normalized_title
            or article.title
        )

        clustering_input = StoryClusteringInput(
            article_id=article.id,
            language_code=article.language_code,
            article_time=(
                article.published_at
                or article.created_at
            ),
            title_terms=extract_title_terms(
                feature_title
            ),
            entity_ids=entity_ids_by_article[
                article.id
            ],
            topic_ids=topic_ids_by_article[
                article.id
            ],
        )

        candidates = self.repository.list_candidates(
            db,
            article=clustering_input,
            window_hours=window_hours,
            limit=candidate_limit,
        )

        return PreparedStoryClustering(
            article_title=article.title,
            article=clustering_input,
            candidates=candidates,
        )

    def cluster(
        self,
        prepared: PreparedStoryClustering,
    ) -> StoryClusteringResult:
        return self.clusterer.cluster(
            prepared.article,
            prepared.candidates,
        )

    def cluster_article(
        self,
        db: Session,
        *,
        article_id: UUID,
        processing_run_id: UUID,
        clustered_at: datetime,
        window_hours: float,
        candidate_limit: int,
    ) -> AppliedStoryClustering | None:
        self.repository.acquire_clustering_lock(db)

        prepared = self.prepare(
            db,
            article_id=article_id,
            window_hours=window_hours,
            candidate_limit=candidate_limit,
        )

        if prepared is None:
            return None

        result = self.cluster(prepared)

        self._validate_result(
            prepared,
            result,
        )

        return self._apply_result_locked(
            db,
            prepared=prepared,
            result=result,
            processing_run_id=processing_run_id,
            clustered_at=clustered_at,
        )

    def apply_result(
        self,
        db: Session,
        *,
        prepared: PreparedStoryClustering,
        result: StoryClusteringResult,
        processing_run_id: UUID,
        clustered_at: datetime,
    ) -> AppliedStoryClustering:
        self._validate_result(
            prepared,
            result,
        )

        self.repository.acquire_clustering_lock(db)

        return self._apply_result_locked(
            db,
            prepared=prepared,
            result=result,
            processing_run_id=processing_run_id,
            clustered_at=clustered_at,
        )

    @staticmethod
    def _validate_result(
        prepared: PreparedStoryClustering,
        result: StoryClusteringResult,
    ) -> None:
        if not 0.0 <= result.similarity_score <= 1.0:
            raise ValueError(
                "similarity_score must be between zero and one"
            )

        if result.story_id is None:
            return

        candidate_story_ids = {
            candidate.story_id
            for candidate in prepared.candidates
        }

        if result.story_id not in candidate_story_ids:
            raise ValueError(
                "clusterer returned a story "
                "outside the candidate set"
            )

    def _apply_result_locked(
        self,
        db: Session,
        *,
        prepared: PreparedStoryClustering,
        result: StoryClusteringResult,
        processing_run_id: UUID,
        clustered_at: datetime,
    ) -> AppliedStoryClustering:
        existing_run_membership = (
            self.repository.get_membership_by_processing_run(
                db,
                processing_run_id,
            )
        )

        if existing_run_membership is not None:
            return AppliedStoryClustering(
                story_id=existing_run_membership.story_id,
                membership_id=existing_run_membership.id,
                changed=False,
                match_kind=existing_run_membership.match_kind,
            )

        existing = self.repository.get_active_membership(
            db,
            prepared.article.article_id,
            for_update=True,
        )

        if result.story_id is None:
            target_story = self.repository.create_story(
                db,
                language_code=(
                    prepared.article.language_code
                ),
            )
            target_story_id = target_story.id
            match_kind = "created"
        else:
            target_story = self.repository.get_story(
                db,
                result.story_id,
                for_update=True,
            )

            if target_story is None:
                raise ValueError(
                    "clusterer target story is not active"
                )

            if (
                target_story.language_code
                != prepared.article.language_code
            ):
                raise ValueError(
                    "clusterer target story language "
                    "does not match article language"
                )

            target_story_id = target_story.id

            if (
                existing is not None
                and existing.story_id
                == target_story_id
            ):
                match_kind = "retained"
            else:
                match_kind = "matched"

        match_details = self._build_match_details(
            result
        )


        membership = self.repository.replace_membership(
            db,
            story_id=target_story_id,
            article_id=prepared.article.article_id,
            processing_run_id=processing_run_id,
            article_title=prepared.article_title,
            article_time=prepared.article.article_time,
            title_terms=prepared.article.title_terms,
            entity_ids=prepared.article.entity_ids,
            topic_ids=prepared.article.topic_ids,
            similarity_score=result.similarity_score,
            match_kind=match_kind,
            match_details=match_details,
            clustered_at=clustered_at,
        )

        return AppliedStoryClustering(
            story_id=membership.story_id,
            membership_id=membership.id,
            changed=True,
            match_kind=membership.match_kind,
        )

    @staticmethod
    def _build_match_details(
        result: StoryClusteringResult,
    ) -> dict[str, object]:
        details = dict(result.details)

        details["matched_membership_id"] = (
            str(result.matched_membership_id)
            if result.matched_membership_id
            is not None
            else None
        )
        details["matched_article_id"] = (
            str(result.matched_article_id)
            if result.matched_article_id
            is not None
            else None
        )

        return details
