from dataclasses import dataclass
import re
import unicodedata

from app.enums.source_dependency import ArticleProvenanceDetectionMethod


@dataclass(frozen=True, slots=True)
class AgencyProvenanceCandidate:
    source_slug: str
    detection_method: ArticleProvenanceDetectionMethod
    confidence: float
    evidence: str


_AGENCY_ALIASES = {
    "dpa": {"dpa", "deutsche presse agentur"},
    "dts-nachrichtenagentur": {"dts", "dts nachrichtenagentur"},
    "apa": {"apa", "austria presse agentur"},
    "keystone-sda": {
        "keystone sda",
        "keystone sda ats",
        "schweizerische depeschenagentur",
    },
    "pa-media": {"pa media", "press association"},
    "reuters": {"reuters"},
    "associated-press": {
        "ap",
        "ap news",
        "associated press",
        "the associated press",
    },
    "afp": {"afp", "agence france presse"},
    "regiocast-nachrichten": {
        "regiocast nachrichten",
        "regiocast news",
    },
}

_COMMON_PREFIXES = ("by ",)
_COMMON_SUFFIXES = (" staff", " newsroom")
_SEGMENT_SPLIT = re.compile(r"[|/;,()\[\]]+")


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def _candidate_segments(value: str | None) -> set[str]:
    if not value:
        return set()

    segments = {_normalize(value)}
    for raw_part in _SEGMENT_SPLIT.split(value):
        normalized = _normalize(raw_part)
        if normalized:
            segments.add(normalized)

    expanded = set(segments)
    for segment in segments:
        for prefix in _COMMON_PREFIXES:
            if segment.startswith(prefix):
                expanded.add(segment[len(prefix):].strip())
        for suffix in _COMMON_SUFFIXES:
            if segment.endswith(suffix):
                expanded.add(segment[:-len(suffix)].strip())
    return {segment for segment in expanded if segment}


def _match_agency(value: str | None) -> str | None:
    segments = _candidate_segments(value)
    if not segments:
        return None

    matches = {
        slug
        for slug, aliases in _AGENCY_ALIASES.items()
        if any(segment in aliases for segment in segments)
    }
    if len(matches) != 1:
        return None
    return next(iter(matches))


def detect_agency_provenance(
    *,
    author: str | None,
    provider: str | None,
) -> AgencyProvenanceCandidate | None:
    provider_match = _match_agency(provider)
    author_match = _match_agency(author)

    if provider_match and author_match and provider_match != author_match:
        return None

    if provider_match:
        return AgencyProvenanceCandidate(
            source_slug=provider_match,
            detection_method=(
                ArticleProvenanceDetectionMethod.PROVIDER_METADATA
            ),
            confidence=0.95,
            evidence=provider or "",
        )

    if author_match:
        return AgencyProvenanceCandidate(
            source_slug=author_match,
            detection_method=ArticleProvenanceDetectionMethod.BYLINE,
            confidence=0.90,
            evidence=author or "",
        )

    return None
