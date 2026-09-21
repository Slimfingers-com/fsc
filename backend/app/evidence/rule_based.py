import re

from app.evidence.provider import (
    ClaimEvidenceLinkResult,
    EvidenceAnalyzer,
    EvidenceItemResult,
    EvidenceKind,
    EvidenceRelationKind,
    StoryEvidenceAnalysisInput,
    StoryEvidenceAnalysisResult,
)


_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?(?:\s*%)?\b")
_PRESS_RELEASE = (
    "press release",
    "pressemitteilung",
    "news release",
    "media release",
)


class RuleBasedEvidenceAnalyzer(EvidenceAnalyzer):
    provider = "local-rules"
    version = "1.0.0"

    def configuration(self) -> dict[str, object]:
        return {}

    @staticmethod
    def _kind(item) -> EvidenceKind:
        title = (item.article_title or "").casefold()
        text = item.article_text.casefold()

        if any(token in title or token in text[:1000] for token in _PRESS_RELEASE):
            return EvidenceKind.PRESS_RELEASE
        if item.source_type == "ACADEMIC":
            return EvidenceKind.STUDY
        if item.source_type == "PRIMARY_SOURCE":
            if _NUMBER.search(item.claim_text):
                return EvidenceKind.OFFICIAL_DATA
            return EvidenceKind.PRIMARY_SOURCE
        if item.source_type in {
            "NEWS",
            "AGENCY",
            "REGIONAL",
            "ALTERNATIVE",
        }:
            return EvidenceKind.INDEPENDENT_REPORTING
        return EvidenceKind.CONTEXT

    def analyze(
        self,
        story: StoryEvidenceAnalysisInput,
    ) -> StoryEvidenceAnalysisResult:
        evidence = []
        links = []
        evidence_index = 0

        for item in sorted(
            story.claims,
            key=lambda value: (
                str(value.claim_group_id),
                str(value.article_id),
                str(value.claim_id),
            ),
        ):
            if item.direct_quote_texts:
                candidates = tuple(
                    (
                        EvidenceKind.DIRECT_QUOTE,
                        quote,
                    )
                    for quote in item.direct_quote_texts
                )
            else:
                candidates = (
                    (
                        self._kind(item),
                        item.claim_text,
                    ),
                )

            for kind, evidence_text in candidates:
                evidence_index += 1
                key = f"evidence-{evidence_index:05d}"
                confidence = 1.0
                evidence.append(
                    EvidenceItemResult(
                        key=key,
                        claim_id=item.claim_id,
                        evidence_kind=kind,
                        evidence_text=evidence_text,
                        confidence=confidence,
                    )
                )
                links.append(
                    ClaimEvidenceLinkResult(
                        claim_group_id=item.claim_group_id,
                        evidence_key=key,
                        relation_kind=(
                            EvidenceRelationKind.CONTEXT
                            if kind == EvidenceKind.CONTEXT
                            else EvidenceRelationKind.SUPPORTS
                        ),
                        confidence=confidence,
                    )
                )

        return StoryEvidenceAnalysisResult(
            evidence=tuple(evidence),
            links=tuple(links),
        )
