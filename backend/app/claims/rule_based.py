import re

from app.analysis.provider import TextPart
from app.claims.provider import (
    ClaimExtractionInput,
    ClaimExtractionResult,
    ClaimExtractor,
    ExtractedClaim,
    normalize_claim_text,
)


_SENTENCE = re.compile(
    r"[^.!?\n]+(?:[.!?]+|$)",
    re.UNICODE,
)
_WORD = re.compile(
    r"\b[^\W_][\w'’-]*\b",
    re.UNICODE,
)
_NUMBER = re.compile(r"\d")


class RuleBasedClaimExtractor(ClaimExtractor):
    provider = "local-rules"
    version = "1.0.0"

    MIN_WORDS = 4
    MAX_WORDS = 80
    MIN_CHARACTERS = 20

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

            for match in _SENTENCE.finditer(
                field_text
            ):
                start, end = self._trimmed_span(
                    field_text,
                    match.start(),
                    match.end(),
                )

                if start >= end:
                    continue

                claim_text = field_text[
                    start:end
                ]

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
