from uuid import UUID

from app.semantic.provider import cosine_similarity
from app.clustering.provider import (
    StoryCandidate,
    StoryClusterer,
    StoryClusteringInput,
    StoryClusteringResult,
)


_LOW_SIGNAL_TITLE_TERMS = frozenset({
    "arrest", "arrested", "assault", "case", "charge", "charged",
    "charges", "guilty", "man", "officer", "pleaded", "pleads",
    "police", "woman",
    "berät", "bundestag", "erstmals", "reform", "über",
})


class RuleBasedStoryClusterer(StoryClusterer):
    provider = "local-rules"
    version = "7"
    substantial_title_min_shared_terms = 4
    substantial_title_min_jaccard = 0.35
    title_containment_min_shared_terms = 3
    title_containment_threshold = 0.75
    cross_language_min_shared_entities = 2
    cross_language_strong_entity_count = 3
    cross_language_min_shared_title_terms = 3

    def __init__(
        self,
        *,
        min_similarity: float = 0.45,
        single_entity_title_similarity_threshold: float = 0.30,
        semantic_similarity_threshold: float = 0.72,
    ) -> None:
        if not 0 <= min_similarity <= 1:
            raise ValueError(
                "min_similarity must be between 0 and 1"
            )

        if not 0 <= single_entity_title_similarity_threshold <= 1:
            raise ValueError(
                "single_entity_title_similarity_threshold must be between 0 and 1"
            )

        if not 0 <= semantic_similarity_threshold <= 1:
            raise ValueError(
                "semantic_similarity_threshold must be between 0 and 1"
            )

        self.min_similarity = min_similarity
        self.single_entity_title_similarity_threshold = (
            single_entity_title_similarity_threshold
        )
        self.semantic_similarity_threshold = semantic_similarity_threshold

    def configuration(
        self,
    ) -> dict[str, object]:
        return {
            "min_similarity": self.min_similarity,
            "single_entity_title_similarity_threshold": (
                self.single_entity_title_similarity_threshold
            ),
            "semantic_similarity_threshold": (
                self.semantic_similarity_threshold
            ),
            "substantial_title_min_shared_terms": (
                self.substantial_title_min_shared_terms
            ),
            "substantial_title_min_jaccard": (
                self.substantial_title_min_jaccard
            ),
            "title_containment_min_shared_terms": (
                self.title_containment_min_shared_terms
            ),
            "title_containment_threshold": (
                self.title_containment_threshold
            ),
            "cross_language_min_shared_entities": (
                self.cross_language_min_shared_entities
            ),
            "cross_language_strong_entity_count": (
                self.cross_language_strong_entity_count
            ),
            "cross_language_min_shared_title_terms": (
                self.cross_language_min_shared_title_terms
            ),
            "low_signal_title_terms": sorted(
                _LOW_SIGNAL_TITLE_TERMS
            ),
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
        left: tuple[object, ...],
        right: tuple[object, ...],
    ) -> int:
        return len(
            set(left) & set(right)
        )

    @staticmethod
    def _overlap_coefficient(
        left: tuple[object, ...],
        right: tuple[object, ...],
    ) -> float:
        left_set = set(left)
        right_set = set(right)
        if not left_set or not right_set:
            return 0.0
        return len(left_set & right_set) / min(
            len(left_set),
            len(right_set),
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

        shared_title_terms = self._shared_count(
            article.title_terms,
            candidate.title_terms,
        )
        title_overlap = self._overlap_coefficient(
            article.title_terms,
            candidate.title_terms,
        )
        shared_entities = self._shared_count(
            article.entity_ids,
            candidate.entity_ids,
        )
        shared_topics = self._shared_count(
            article.topic_ids,
            candidate.topic_ids,
        )

        semantic_similarity = 0.0
        semantic_match = False
        if (
            article.semantic_embedding
            and candidate.semantic_embedding
            and article.semantic_model
            and article.semantic_model == candidate.semantic_model
        ):
            semantic_similarity = max(
                0.0,
                cosine_similarity(
                    article.semantic_embedding,
                    candidate.semantic_embedding,
                ),
            )
            semantic_match = (
                semantic_similarity
                >= self.semantic_similarity_threshold
            )

        cross_language = (
            article.language_code
            != candidate.language_code
        )
        shared_title_term_values = (
            set(article.title_terms)
            & set(candidate.title_terms)
        )
        low_signal_title_only = (
            not cross_language
            and shared_entities == 0
            and bool(shared_title_term_values)
            and shared_title_term_values.issubset(
                _LOW_SIGNAL_TITLE_TERMS
            )
        )
        strong_title_match = (
            not cross_language
            and not low_signal_title_only
            and title_similarity >= 0.50
        )
        substantial_title_match = (
            not cross_language
            and not low_signal_title_only
            and shared_title_terms
            >= self.substantial_title_min_shared_terms
            and title_similarity
            >= self.substantial_title_min_jaccard
        )
        title_containment_match = (
            not cross_language
            and not low_signal_title_only
            and shared_title_terms
            >= self.title_containment_min_shared_terms
            and title_overlap >= self.title_containment_threshold
        )
        entity_title_match = (
            not cross_language
            and shared_entities >= 1
            and title_similarity
            >= self.single_entity_title_similarity_threshold
        )
        multi_entity_match = (
            not cross_language
            and shared_entities >= 2
        )
        cross_language_entity_match = (
            cross_language
            and shared_entities
            >= self.cross_language_min_shared_entities
            and entity_similarity >= 0.50
            and (
                shared_entities
                >= self.cross_language_strong_entity_count
                or shared_title_terms
                >= self.cross_language_min_shared_title_terms
            )
        )

        if cross_language:
            if not (
                semantic_match
                or cross_language_entity_match
            ):
                return None
        elif not (
            strong_title_match
            or substantial_title_match
            or title_containment_match
            or entity_title_match
            or multi_entity_match
            or semantic_match
        ):
            return None

        weighted_similarity = (
            0.55 * title_similarity
            + 0.30 * entity_similarity
            + 0.15 * topic_similarity
        )

        if cross_language:
            similarity = max(
                entity_similarity
                if cross_language_entity_match
                else 0.0,
                semantic_similarity,
            )
        else:
            title_overlap_similarity = (
                title_overlap
                if (
                    substantial_title_match
                    or title_containment_match
                )
                else 0.0
            )
            similarity = max(
                title_similarity,
                title_overlap_similarity,
                weighted_similarity,
                semantic_similarity,
            )

        if similarity < self.min_similarity:
            return None

        match_basis = []
        if strong_title_match:
            match_basis.append("title")
        if substantial_title_match:
            match_basis.append("substantial_title")
        if title_containment_match:
            match_basis.append("title_containment")
        if entity_title_match:
            match_basis.append("entity_title")
        if multi_entity_match:
            match_basis.append("multi_entity")
        if cross_language_entity_match:
            match_basis.append("cross_language_entities")
        if semantic_match:
            match_basis.append("semantic")

        return (
            similarity,
            {
                "title_similarity": title_similarity,
                "title_overlap": title_overlap,
                "shared_title_terms": shared_title_terms,
                "low_signal_title_only": low_signal_title_only,
                "entity_similarity": entity_similarity,
                "topic_similarity": topic_similarity,
                "shared_entities": shared_entities,
                "shared_topics": shared_topics,
                "semantic_similarity": semantic_similarity,
                "semantic_model": (
                    article.semantic_model
                    if semantic_match
                    else None
                ),
                "cross_language": cross_language,
                "language_pair": [
                    article.language_code,
                    candidate.language_code,
                ],
                "match_basis": match_basis,
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
