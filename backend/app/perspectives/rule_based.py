import re

from app.analysis.provider import TextPart
from app.perspectives.provider import (
    PerspectiveAnalysisInput,
    PerspectiveAnalysisResult,
    PerspectiveAnalyzer,
    PerspectiveAttribution,
    PerspectiveClaimInput,
    PerspectiveEntityMentionInput,
    PerspectiveKind,
)


_SENTENCE = re.compile(
    r"[^.!?\n]+(?:[.!?]+|$)",
    re.UNICODE,
)

_REPORT_VERB = re.compile(
    r"\b("
    r"says|said|states?|stated|announces?|announced|"
    r"claims?|claimed|argues?|argued|warns?|warned|"
    r"confirms?|confirmed|told|"
    r"sagt|sagte|erklärt|erklaert|erklärte|erklaerte|"
    r"kündigt|kuendigt|kündigte|kuendigte|"
    r"behauptet|behauptete|argumentiert|argumentierte|"
    r"warnt|warnte|bestätigt|bestaetigt|bestätigte|bestaetigte"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

_REPORT_PREFIX = re.compile(
    r"(according\s+to|laut|zufolge)\s*$",
    re.IGNORECASE | re.UNICODE,
)

_QUOTE_CHARACTER = re.compile(r'["“”„«»]')


class RuleBasedPerspectiveAnalyzer(PerspectiveAnalyzer):
    provider = "local-rules"
    version = "1.0.0"

    @staticmethod
    def _field_text(
        article: PerspectiveAnalysisInput,
        text_source: TextPart,
    ) -> str:
        if text_source == TextPart.TITLE:
            return article.title
        return article.normalized_text

    @classmethod
    def _evidence_span(
        cls,
        article: PerspectiveAnalysisInput,
        claim: PerspectiveClaimInput,
    ) -> tuple[int, int]:
        field_text = cls._field_text(
            article,
            claim.text_source,
        )

        for sentence_index, match in enumerate(
            _SENTENCE.finditer(field_text)
        ):
            if sentence_index != claim.sentence_index:
                continue

            start = match.start()
            end = match.end()

            while start < end and field_text[start].isspace():
                start += 1
            while end > start and field_text[end - 1].isspace():
                end -= 1

            if (
                start <= claim.start_offset
                and claim.end_offset <= end
            ):
                return start, end

        return claim.start_offset, claim.end_offset

    @staticmethod
    def _attribution_candidate(
        *,
        evidence_text: str,
        evidence_start: int,
        claim: PerspectiveClaimInput,
        mention: PerspectiveEntityMentionInput,
    ) -> tuple[int, int] | None:
        if (
            mention.start_offset is None
            or mention.end_offset is None
            or mention.text_source != claim.text_source
        ):
            return None

        relative_start = (
            mention.start_offset
            - evidence_start
        )
        relative_end = (
            mention.end_offset
            - evidence_start
        )

        if (
            relative_start < 0
            or relative_end
            > len(evidence_text)
        ):
            return None

        before = evidence_text[
            max(0, relative_start - 48):
            relative_start
        ]
        after = evidence_text[
            relative_end:
            min(
                len(evidence_text),
                relative_end + 80,
            )
        ]

        after_head = after.lstrip(
            " \t,:;-–—"
        )
        has_after_verb = bool(
            _REPORT_VERB.match(
                after_head
            )
        )
        has_prefix = bool(
            _REPORT_PREFIX.search(before)
        )

        if not (
            has_after_verb
            or has_prefix
        ):
            return None

        distance = min(
            abs(
                mention.start_offset
                - claim.start_offset
            ),
            abs(
                mention.end_offset
                - claim.end_offset
            ),
        )

        return (
            distance,
            mention.start_offset,
        )

    def analyze(
        self,
        article: PerspectiveAnalysisInput,
    ) -> PerspectiveAnalysisResult:
        attributions: list[
            PerspectiveAttribution
        ] = []

        for claim in article.claims:
            field_text = self._field_text(
                article,
                claim.text_source,
            )
            evidence_start, evidence_end = (
                self._evidence_span(
                    article,
                    claim,
                )
            )
            evidence_text = field_text[
                evidence_start:evidence_end
            ]

            candidates: list[
                tuple[
                    tuple[int, int],
                    PerspectiveEntityMentionInput,
                ]
            ] = []

            for mention in article.entity_mentions:
                candidate = (
                    self._attribution_candidate(
                        evidence_text=evidence_text,
                        evidence_start=evidence_start,
                        claim=claim,
                        mention=mention,
                    )
                )

                if candidate is not None:
                    candidates.append(
                        (
                            candidate,
                            mention,
                        )
                    )

            candidates.sort(
                key=lambda item: (
                    item[0],
                    str(item[1].entity_id),
                    str(item[1].mention_id),
                )
            )

            if candidates:
                mention = candidates[0][1]
                kind = (
                    PerspectiveKind.QUOTED
                    if _QUOTE_CHARACTER.search(
                        evidence_text
                    )
                    else PerspectiveKind.REPORTED
                )
                confidence = (
                    0.88
                    if kind
                    == PerspectiveKind.QUOTED
                    else 0.82
                )
                holder_mention_id = (
                    mention.mention_id
                )
            else:
                kind = (
                    PerspectiveKind.UNATTRIBUTED
                )
                confidence = 0.68
                holder_mention_id = None

            attributions.append(
                PerspectiveAttribution(
                    claim_id=claim.claim_id,
                    perspective_kind=kind,
                    holder_mention_id=(
                        holder_mention_id
                    ),
                    evidence_text=(
                        evidence_text
                    ),
                    text_source=(
                        claim.text_source
                    ),
                    start_offset=(
                        evidence_start
                    ),
                    end_offset=(
                        evidence_end
                    ),
                    sentence_index=(
                        claim.sentence_index
                    ),
                    confidence=confidence,
                )
            )

        return PerspectiveAnalysisResult(
            attributions=tuple(
                attributions
            )
        )
