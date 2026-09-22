from enum import Enum


class ReachMetricQuality(str, Enum):
    AUDITED = "AUDITED"
    PUBLISHER_REPORTED = "PUBLISHER_REPORTED"
    THIRD_PARTY_ESTIMATE = "THIRD_PARTY_ESTIMATE"
    OTHER = "OTHER"
