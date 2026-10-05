import re
import unicodedata


TITLE_FEATURE_VERSION = "2"

_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_NEWS_COMPACT_BOILERPLATE = re.compile(
    r"\bnews\s+kompakt\s*:?\s*das\s+wichtigste\s+kurz\s+gefasst\b"
)

_STOPWORDS = frozenset(
    {
        "aber",
        "als",
        "auch",
        "auf",
        "aus",
        "bei",
        "das",
        "dem",
        "den",
        "der",
        "des",
        "die",
        "ein",
        "eine",
        "einer",
        "eines",
        "für",
        "hat",
        "ist",
        "mit",
        "nach",
        "nicht",
        "oder",
        "sich",
        "und",
        "von",
        "vor",
        "wie",
        "wird",
        "zu",
        "zum",
        "zur",
        "and",
        "are",
        "for",
        "from",
        "has",
        "have",
        "into",
        "not",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)


def extract_title_terms(
    title: str | None,
) -> tuple[str, ...]:
    if not title:
        return ()

    normalized = unicodedata.normalize(
        "NFKC",
        title,
    ).casefold()
    normalized = _NEWS_COMPACT_BOILERPLATE.sub(
        " ",
        normalized,
    )

    terms = {
        token
        for token in _WORD_PATTERN.findall(normalized)
        if len(token) >= 3
        and token not in _STOPWORDS
    }

    return tuple(sorted(terms))
