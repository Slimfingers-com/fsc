from uuid import UUID

from app.clustering.provider import (
    StoryCandidate,
    StoryClusterer,
    StoryClusteringInput,
    StoryClusteringResult,
)


class RuleBasedStoryClusterer(StoryClusterer):
    provider = "local-rules"
    version = "1"

    def __init__(
        self,
        *,
        min_similarity: float = 0.45,
    ) -> None:
        if not 0 <= min_similarity <= 1:
            raise ValueError(
                "min_similarity must be between 0 and 1"
            )

        self.min_similarity = min_similarity

    def configuration(
        self,
    ) -> dict[str, object]:
        return {
            "min_similarity": self.min_similarity,
        }

    @staticmethod
    def _jaccard(
        left: tuple[object, ...],
        right: tuple[object, ...],
    ) -> float:
        left_set = set(left)
        right_set = set(right)

        if not left_set or not right_set:
            return 0.0

        return len(
            left_set & right_set
        ) / len(
            left_set | right_set
        )

    @staticmethod
    def _shared_count(
        left: tuple[UUID, ...],
        right: tuple[UUID, ...],
    ) -> int:
        return len(
            set(left) & set(right)
        )

    def _score(
        self,
        article: StoryClusteringInput,
        candidate: StoryCandidate,
    ) -> tuple[float, dict[str, object]] | None:
        title_similarity = self._jaccard(
            article.title_terms,
            candidate.title_terms,
        )
        entity_similarity = self._jaccard(
            article.entity_ids,
            candidate.entity_ids,
        )
        topic_similarity = self._jaccard(
            article.topic_ids,
            candidate.topic_ids,
        )

        shared_entities = self._shared_count(
            article.entity_ids,
            candidate.entity_ids,
        )
        shared_topics = self._shared_count(
            article.topic_ids,
            candidate.topic_ids,
        )

        strong_title_match = (
            title_similarity >= 0.50
        )
        entity_title_match = (
            shared_entities >= 1
            and title_similarity >= 0.15
        )
        multi_entity_match = (
            shared_entities >= 2
        )

        if not (
            strong_title_match
            or entity_title_match
            or multi_entity_match
        ):
            return None

        weighted_similarity = (
            0.55 * title_similarity
            + 0.30 * entity_similarity
            + 0.15 * topic_similarity
        )

        similarity = max(
            title_similarity,
            weighted_similarity,
        )

        if similarity < self.min_similarity:
            return None

        return (
            similarity,
            {
                "title_similarity": title_similarity,
                "entity_similarity": entity_similarity,
                "topic_similarity": topic_similarity,
                "shared_entities": shared_entities,
                "shared_topics": shared_topics,
            },
        )

    def cluster(
        self,
        article: StoryClusteringInput,
        candidates: tuple[StoryCandidate, ...],
    ) -> StoryClusteringResult:
        best_candidate: StoryCandidate | None = None
        best_score = 0.0
        best_details: dict[str, object] = {}

        for candidate in candidates:
            scored = self._score(
                article,
                candidate,
            )

            if scored is None:
                continue

            score, details = scored

            if best_candidate is None:
                best_candidate = candidate
                best_score = score
                best_details = details
                continue

            if score > best_score:
                best_candidate = candidate
                best_score = score
                best_details = details
                continue

            if score < best_score:
                continue

            if (
                candidate.article_time
                > best_candidate.article_time
            ):
                best_candidate = candidate
                best_details = details
                continue

            if (
                candidate.article_time
                == best_candidate.article_time
                and str(candidate.story_id)
                < str(best_candidate.story_id)
            ):
                best_candidate = candidate
                best_details = details

        if best_candidate is None:
            return StoryClusteringResult(
                story_id=None,
                similarity_score=0.0,
                matched_membership_id=None,
                matched_article_id=None,
                details={
                    "candidate_count": len(candidates),
                },
            )

        return StoryClusteringResult(
            story_id=best_candidate.story_id,
            similarity_score=best_score,
            matched_membership_id=best_candidate.membership_id,
            matched_article_id=best_candidate.article_id,
            details={
                **best_details,
                "candidate_count": len(candidates),
                "matched_membership_id": str(
                    best_candidate.membership_id
                ),
                "matched_article_id": str(
                    best_candidate.article_id
                ),
            },
        )
