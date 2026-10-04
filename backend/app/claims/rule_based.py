import re

from app.analysis.provider import TextPart
from app.claims.provider import (
    ClaimExtractionInput,
    ClaimExtractionResult,
    ClaimExtractor,
    ExtractedClaim,
    normalize_claim_text,
)


_WORD = re.compile(
    r"\b[^\W_][\w'’-]*\b",
    re.UNICODE,
)
_NUMBER = re.compile(r"\d")
_TRAILING_CLOSERS = frozenset('"\'’”»)]}')

_COMMON_ABBREVIATIONS = frozenset(
    {
        "mr",
        "mrs",
        "ms",
        "dr",
        "prof",
        "sr",
        "jr",
        "st",
        "no",
        "nr",
        "ca",
        "bzw",
        "etc",
        "vs",
        "resp",
    }
)
_DOTTED_INITIALISM = re.compile(
    r"(?:^|[^A-Za-z])(?:[A-Za-z]\.){2,}$"
)

_GERMAN_MONTHS = frozenset(
    {
        "januar",
        "februar",
        "märz",
        "maerz",
        "april",
        "mai",
        "juni",
        "juli",
        "august",
        "september",
        "oktober",
        "november",
        "dezember",
    }
)
_GERMAN_ORDINAL_CONTEXT = frozenset(
    {
        "am",
        "an",
        "vom",
        "zum",
        "zur",
        "im",
        "beim",
        "dem",
        "den",
        "der",
        "des",
        "das",
        "die",
        "ein",
        "eine",
        "einem",
        "einen",
        "einer",
        "eines",
        "sein",
        "seine",
        "seinem",
        "seinen",
        "seiner",
        "seines",
        "ihr",
        "ihre",
        "ihrem",
        "ihren",
        "ihrer",
        "ihres",
        "nach",
        "vor",
        "seit",
        "gegen",
        "bis",
        "ab",
        "anlässlich",
        "anlaesslich",
    }
)

_PUBLISHING_META = (
    re.compile(r"^\s*read in full\s*:", re.IGNORECASE),
    re.compile(
        r"\b(?:appeared first on|first appeared on|originally appeared on)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*our standards\s*:", re.IGNORECASE),
    re.compile(
        r"\b(?:pic\.)?(?:twitter|x)\.com/",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(newsblog|liveblog)\b.*\b"
        r"(auf dem laufenden|zum nachlesen)\b",
        re.IGNORECASE,
    ),
)
_PUBLISHING_FOOTER_BLOCK = re.compile(
    r"\bthe post\b"
    r".{0,1200}?"
    r"\b(?:appeared first on|first appeared on|originally appeared on)\b"
    r".{0,250}?"
    r"(?:[.!?](?=\s|$)|$)",
    re.IGNORECASE | re.DOTALL,
)


class RuleBasedClaimExtractor(ClaimExtractor):
    provider = "local-rules"
    version = "1.1.1"

    MIN_WORDS = 4
    MAX_WORDS = 80
    MIN_CHARACTERS = 20

    @staticmethod
    def _trimmed_span(
        text: str,
        start: int,
        end: int,
    ) -> tuple[int, int]:
        while (
            start < end
            and text[start].isspace()
        ):
            start += 1

        while (
            end > start
            and text[end - 1].isspace()
        ):
            end -= 1

        return start, end

    @staticmethod
    def _token_before(
        text: str,
        index: int,
    ) -> str:
        position = index - 1
        while (
            position >= 0
            and text[position].isspace()
        ):
            position -= 1

        end = position + 1
        while (
            position >= 0
            and (
                text[position].isalnum()
                or text[position] in "_'’"
            )
        ):
            position -= 1

        return text[
            position + 1:end
        ]

    @staticmethod
    def _token_after(
        text: str,
        index: int,
    ) -> str:
        position = index
        length = len(text)
        while (
            position < length
            and text[position].isspace()
        ):
            position += 1

        start = position
        while (
            position < length
            and (
                text[position].isalnum()
                or text[position] in "_'’"
            )
        ):
            position += 1

        return text[start:position]

    @classmethod
    def _previous_word_before_number(
        cls,
        text: str,
        period_index: int,
    ) -> str:
        position = period_index - 1
        while (
            position >= 0
            and text[position].isdigit()
        ):
            position -= 1

        return cls._token_before(
            text,
            position + 1,
        ).lower()

    @classmethod
    def _protected_period(
        cls,
        text: str,
        index: int,
        language_code: str | None,
    ) -> bool:
        if index <= 0:
            return False

        previous = text[index - 1]
        following = (
            text[index + 1]
            if index + 1 < len(text)
            else ""
        )

        # Decimal numbers, grouped thousands and clock forms such as
        # 2.5, 40.000 or 11.30pm must stay inside one sentence.
        if (
            previous.isdigit()
            and following.isdigit()
        ):
            return True

        before = cls._token_before(
            text,
            index,
        )

        # Keep the interior dot of initialisms such as U.S., U.N. and
        # e.g. without treating an arbitrary missing space after a real
        # sentence boundary ("... ended.Next ...") as an abbreviation.
        if (
            len(before) == 1
            and previous.isalpha()
            and following.isalpha()
        ):
            return True

        after = cls._token_after(
            text,
            index + 1,
        )

        if (
            before.lower()
            in _COMMON_ABBREVIATIONS
            and after
        ):
            return True

        prefix = text[
            max(0, index - 12):
            index + 1
        ]
        if (
            _DOTTED_INITIALISM.search(
                prefix
            )
            and after
        ):
            return True

        # German ordinals use a trailing full stop. Protect common date
        # and ordinal contexts without treating every number at a real
        # sentence end as an ordinal.
        if (
            (language_code or "")
            .lower()
            .startswith("de")
            and before.isdigit()
            and after
        ):
            if (
                after.lower()
                in _GERMAN_MONTHS
            ):
                return True

            previous_word = (
                cls._previous_word_before_number(
                    text,
                    index,
                )
            )
            if (
                previous_word
                in _GERMAN_ORDINAL_CONTEXT
            ):
                return True

        return False

    @classmethod
    def _sentence_spans(
        cls,
        text: str,
        language_code: str | None,
    ):
        start = 0
        index = 0
        length = len(text)

        while index < length:
            character = text[index]

            if character == "\n":
                span = cls._trimmed_span(
                    text,
                    start,
                    index,
                )
                if span[0] < span[1]:
                    yield span
                index += 1
                start = index
                continue

            boundary = character in "!?…"
            if (
                character == "."
                and not cls._protected_period(
                    text,
                    index,
                    language_code,
                )
            ):
                boundary = True

            if not boundary:
                index += 1
                continue

            end = index + 1
            while (
                end < length
                and text[end] in ".!?…"
            ):
                end += 1
            while (
                end < length
                and text[end]
                in _TRAILING_CLOSERS
            ):
                end += 1

            span = cls._trimmed_span(
                text,
                start,
                end,
            )
            if span[0] < span[1]:
                yield span

            start = end
            index = end

        span = cls._trimmed_span(
            text,
            start,
            length,
        )
        if span[0] < span[1]:
            yield span

    @staticmethod
    def _publishing_footer_spans(
        text: str,
    ) -> tuple[tuple[int, int], ...]:
        if not text:
            return ()

        search_start = max(
            0,
            len(text) - 2500,
        )
        suffix = text[search_start:]
        return tuple(
            (
                search_start + match.start(),
                search_start + match.end(),
            )
            for match in _PUBLISHING_FOOTER_BLOCK.finditer(
                suffix
            )
        )

    @staticmethod
    def _overlaps_any(
        start: int,
        end: int,
        spans: tuple[tuple[int, int], ...],
    ) -> bool:
        return any(
            start < span_end
            and end > span_start
            for span_start, span_end in spans
        )

    @classmethod
    def _candidate(
        cls,
        text: str,
    ) -> bool:
        stripped = text.strip()

        if (
            len(stripped)
            < cls.MIN_CHARACTERS
            or stripped.endswith("?")
        ):
            return False

        without_closers = stripped.rstrip(
            "".join(_TRAILING_CLOSERS)
        )
        if (
            without_closers.endswith("…")
            or without_closers.endswith("...")
        ):
            return False

        if any(
            pattern.search(stripped)
            for pattern in _PUBLISHING_META
        ):
            return False

        words = _WORD.findall(
            stripped
        )

        if not (
            cls.MIN_WORDS
            <= len(words)
            <= cls.MAX_WORDS
        ):
            return False

        return any(
            character.isalpha()
            for character in stripped
        )

    def extract(
        self,
        article: ClaimExtractionInput,
    ) -> ClaimExtractionResult:
        claims: list[ExtractedClaim] = []
        seen: set[str] = set()

        fields = (
            (
                TextPart.TITLE,
                article.title,
            ),
            (
                TextPart.BODY,
                article.normalized_text,
            ),
        )

        for text_source, field_text in fields:
            sentence_index = 0
            publishing_footer_spans = (
                self._publishing_footer_spans(
                    field_text
                )
            )

            for start, end in self._sentence_spans(
                field_text,
                article.language_code,
            ):
                claim_text = field_text[
                    start:end
                ]

                if self._overlaps_any(
                    start,
                    end,
                    publishing_footer_spans,
                ):
                    sentence_index += 1
                    continue

                if not self._candidate(
                    claim_text
                ):
                    sentence_index += 1
                    continue

                normalized = normalize_claim_text(
                    claim_text
                )

                if normalized in seen:
                    sentence_index += 1
                    continue

                seen.add(normalized)

                confidence = (
                    0.66
                    if text_source
                    == TextPart.TITLE
                    else 0.72
                )

                if _NUMBER.search(
                    claim_text
                ):
                    confidence += 0.04

                if claim_text.endswith(
                    (".", "!")
                ):
                    confidence += 0.02

                claims.append(
                    ExtractedClaim(
                        claim_text=claim_text,
                        text_source=(
                            text_source
                        ),
                        start_offset=start,
                        end_offset=end,
                        sentence_index=(
                            sentence_index
                        ),
                        confidence=min(
                            confidence,
                            0.9,
                        ),
                    )
                )

                sentence_index += 1

        return ClaimExtractionResult(
            claims=tuple(claims)
        )
