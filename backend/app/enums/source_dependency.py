from enum import StrEnum


class SourceRelationKind(StrEnum):
    EDITORIAL_PARENT = "editorial_parent"
    SHARED_NEWSROOM = "shared_newsroom"
    CONTENT_SUPPLIER = "content_supplier"
    SYNDICATION_PARTNER = "syndication_partner"
    JOINT_EDITORIAL_OPERATION = "joint_editorial_operation"


class ArticleProvenanceKind(StrEnum):
    SUPPLIED_BY = "supplied_by"
    SYNDICATED_FROM = "syndicated_from"
    REPUBLISHED_FROM = "republished_from"
    CO_PRODUCED_WITH = "co_produced_with"


class ArticleProvenanceDetectionMethod(StrEnum):
    MANUAL = "manual"
    FEED_METADATA = "feed_metadata"
    PROVIDER_METADATA = "provider_metadata"
    CANONICAL_URL = "canonical_url"
    BYLINE = "byline"
    CONTENT_SIMILARITY = "content_similarity"
    OTHER = "other"
