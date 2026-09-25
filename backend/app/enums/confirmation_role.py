from enum import StrEnum

from app.enums.source_type import SourceType


class ConfirmationRole(StrEnum):
    EDITORIAL = "editorial"
    EXPERT_ANALYSIS = "expert_analysis"
    PRIMARY_EVIDENCE = "primary_evidence"
    ADVOCACY = "advocacy"
    SIGNAL = "signal"


INDEPENDENT_CONFIRMATION_ROLES = {
    ConfirmationRole.EDITORIAL,
    ConfirmationRole.EXPERT_ANALYSIS,
}


def counts_as_independent_confirmation(
    role: ConfirmationRole | str,
) -> bool:
    try:
        value = (
            role
            if isinstance(role, ConfirmationRole)
            else ConfirmationRole(role)
        )
    except ValueError:
        return False
    return value in INDEPENDENT_CONFIRMATION_ROLES


def default_confirmation_role(
    source_type: SourceType | str,
) -> ConfirmationRole:
    value = (
        source_type
        if isinstance(source_type, SourceType)
        else SourceType(source_type)
    )
    if value is SourceType.PRIMARY_SOURCE:
        return ConfirmationRole.PRIMARY_EVIDENCE
    if value in {
        SourceType.NGO,
        SourceType.INTEREST_GROUP,
        SourceType.COMPANY,
    }:
        return ConfirmationRole.ADVOCACY
    if value in {SourceType.ACADEMIC, SourceType.THINK_TANK}:
        return ConfirmationRole.EXPERT_ANALYSIS
    if value is SourceType.SIGNAL:
        return ConfirmationRole.SIGNAL
    return ConfirmationRole.EDITORIAL
