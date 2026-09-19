import re
import unicodedata


TITLE_FEATURE_VERSION = "1"

_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)

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
        "fÃ¼r",
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

    terms = {
        token
        for token in _WORD_PATTERN.findall(normalized)
        if len(token) >= 3
        and token not in _STOPWORDS
    }

    return tuple(sorted(terms))
