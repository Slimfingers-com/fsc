from enum import StrEnum


class ArticlePipeline(StrEnum):
    NORMALIZATION = "normalization"
    SEARCH_INDEXING = "search_indexing"
    ENTITY_TOPIC = "entity_topic"
    SEMANTIC_EMBEDDING = "semantic_embedding"
    STORY_CLUSTERING = "story_clustering"
    CLAIM_EXTRACTION = "claim_extraction"
    PERSPECTIVE_ANALYSIS = "perspective_analysis"
    EVIDENCE_ANALYSIS = "evidence_analysis"
    COVERAGE_ANALYSIS = "coverage_analysis"
