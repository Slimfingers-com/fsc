from enum import StrEnum


class StoryPipeline(StrEnum):
    CLAIM_RELATIONS = "claim_relations"
    EVIDENCE_ANALYSIS = "evidence_analysis"
    CONSENSUS_ANALYSIS = "consensus_analysis"
