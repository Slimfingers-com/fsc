import pytest

from app.enums.confirmation_role import (
    ConfirmationRole,
    counts_as_independent_confirmation,
    default_confirmation_role,
)
from app.enums.source_type import SourceType


@pytest.mark.parametrize(
    ("source_type", "expected"),
    [
        (SourceType.NEWS, ConfirmationRole.EDITORIAL),
        (SourceType.AGENCY, ConfirmationRole.EDITORIAL),
        (SourceType.REGIONAL, ConfirmationRole.EDITORIAL),
        (SourceType.ALTERNATIVE, ConfirmationRole.EDITORIAL),
        (SourceType.PRIMARY_SOURCE, ConfirmationRole.PRIMARY_EVIDENCE),
        (SourceType.NGO, ConfirmationRole.ADVOCACY),
        (SourceType.INTEREST_GROUP, ConfirmationRole.ADVOCACY),
        (SourceType.COMPANY, ConfirmationRole.ADVOCACY),
        (SourceType.ACADEMIC, ConfirmationRole.EXPERT_ANALYSIS),
        (SourceType.THINK_TANK, ConfirmationRole.EXPERT_ANALYSIS),
        (SourceType.SIGNAL, ConfirmationRole.SIGNAL),
    ],
)
def test_default_confirmation_role(source_type, expected):
    assert default_confirmation_role(source_type) is expected


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (ConfirmationRole.EDITORIAL, True),
        (ConfirmationRole.EXPERT_ANALYSIS, True),
        (ConfirmationRole.PRIMARY_EVIDENCE, False),
        (ConfirmationRole.ADVOCACY, False),
        (ConfirmationRole.SIGNAL, False),
    ],
)
def test_independent_confirmation_eligibility(role, expected):
    assert counts_as_independent_confirmation(role) is expected
