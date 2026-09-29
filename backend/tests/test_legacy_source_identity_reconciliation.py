import pytest

from app.core.exceptions import BusinessRuleViolationError
from app.enums.coverage_scope import CoverageScope
from app.enums.source_metadata import PublicationForm, SourceMedium
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate
from app.schemas.source import SourceCreate
from app.schemas.source_metadata import SourceOutletCreate
from app.services.legacy_source_identity_reconciliation import (
    CanonicalOutletSpec,
    LEGACY_SOURCE_IDENTITY_SPECS,
    LegacySourceIdentityReconciler,
    LegacySourceIdentitySpec,
)
from app.services.source import SourceService


def _spec() -> LegacySourceIdentitySpec:
    return LegacySourceIdentitySpec(
        legacy_slug="deutschlandfunk",
        accepted_names=("Deutschlandfunk", "Deutschlandradio"),
        canonical_name="Deutschlandradio",
        canonical_url="https://www.deutschlandradio.de/",
        source_type=SourceType.NEWS,
        coverage_scope=CoverageScope.NATIONAL,
        country="DE",
        language="de",
        outlets=(
            CanonicalOutletSpec(
                name="Deutschlandfunk",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.RADIO,
                url="https://www.deutschlandfunk.de/",
                is_primary=True,
            ),
            CanonicalOutletSpec(
                name="Deutschlandfunk Kultur",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.RADIO,
                url="https://www.deutschlandfunkkultur.de/",
            ),
        ),
    )


def _create_legacy_source(db):
    return SourceService().create_source(
        db,
        SourceCreate(
            name="Deutschlandfunk",
            url="https://www.deutschlandfunk.de/",
            source_type=SourceType.NEWS,
            coverage_scope=CoverageScope.NATIONAL,
            country="DE",
            language="de",
            priority_tier=1,
            feeds=[
                FeedCreate(
                    name="Nachrichten",
                    url="https://www.deutschlandfunk.de/nachrichten-100.rss",
                    priority=1,
                    fetch_interval_minutes=15,
                )
            ],
        ),
    )


def test_legacy_identity_dry_run_does_not_mutate(db) -> None:
    source = _create_legacy_source(db)
    source_id = source.id
    feed_id = source.feeds[0].id

    report = LegacySourceIdentityReconciler(
        specs=[_spec()]
    ).reconcile(db)

    assert report.has_conflicts is False
    assert report.change_count == 4
    assert [action.action for action in report.actions] == [
        "canonicalize_source_name",
        "update_source_url",
        "create_outlet",
        "create_outlet",
    ]

    unchanged = SourceService().get_by_slug(db, "deutschlandfunk")
    assert unchanged is not None
    assert unchanged.id == source_id
    assert unchanged.name == "Deutschlandfunk"
    assert unchanged.slug == "deutschlandfunk"
    assert unchanged.url == "https://www.deutschlandfunk.de/"
    assert unchanged.feeds[0].id == feed_id
    assert unchanged.outlets == []


def test_legacy_identity_apply_preserves_source_slug_uuid_and_feed_id(db) -> None:
    source = _create_legacy_source(db)
    source_id = source.id
    feed_id = source.feeds[0].id

    report = LegacySourceIdentityReconciler(
        specs=[_spec()]
    ).reconcile(
        db,
        apply=True,
    )

    assert report.has_conflicts is False
    assert report.change_count == 4

    canonical = SourceService().get_by_slug(db, "deutschlandfunk")
    assert canonical is not None
    assert canonical.id == source_id
    assert canonical.slug == "deutschlandfunk"
    assert canonical.name == "Deutschlandradio"
    assert canonical.normalized_name == "deutschlandradio"
    assert canonical.url == "https://www.deutschlandradio.de/"
    assert canonical.feeds[0].id == feed_id
    assert canonical.feeds[0].source_id == source_id

    assert [
        (
            outlet.name,
            outlet.media_category,
            outlet.publication_form,
            outlet.is_primary,
        )
        for outlet in canonical.outlets
    ] == [
        (
            "Deutschlandfunk",
            SourceMedium.BROADCAST,
            PublicationForm.RADIO,
            True,
        ),
        (
            "Deutschlandfunk Kultur",
            SourceMedium.BROADCAST,
            PublicationForm.RADIO,
            False,
        ),
    ]


def test_legacy_identity_reconciliation_is_idempotent(db) -> None:
    _create_legacy_source(db)
    reconciler = LegacySourceIdentityReconciler(specs=[_spec()])

    reconciler.reconcile(db, apply=True)
    report = reconciler.reconcile(db)

    assert report.has_conflicts is False
    assert report.change_count == 0
    assert len(report.actions) == 1
    assert report.actions[0].action == "no_change"


def test_legacy_identity_conflicts_with_existing_canonical_source(db) -> None:
    _create_legacy_source(db)
    SourceService().create_source(
        db,
        SourceCreate(
            name="Deutschlandradio",
            url="https://www.deutschlandradio.de/",
            source_type=SourceType.NEWS,
            coverage_scope=CoverageScope.NATIONAL,
            country="DE",
            language="de",
        ),
    )

    reconciler = LegacySourceIdentityReconciler(specs=[_spec()])
    report = reconciler.reconcile(db)

    assert report.has_conflicts is True
    assert "belongs to another Source" in report.conflicts[0]

    with pytest.raises(BusinessRuleViolationError):
        reconciler.reconcile(db, apply=True)


def test_legacy_identity_rejects_incompatible_source_type(db) -> None:
    service = SourceService()
    service.create_source(
        db,
        SourceCreate(
            name="Deutschlandfunk",
            url="https://www.deutschlandfunk.de/",
            source_type=SourceType.COMPANY,
            coverage_scope=CoverageScope.NATIONAL,
            country="DE",
            language="de",
        ),
    )

    report = LegacySourceIdentityReconciler(
        specs=[_spec()]
    ).reconcile(db)

    assert report.has_conflicts is True
    assert "SourceType" in report.conflicts[0]


def test_legacy_identity_rejects_conflicting_existing_outlet(db) -> None:
    source = _create_legacy_source(db)
    SourceService().create_outlet(
        db,
        source,
        SourceOutletCreate(
            name="Deutschlandfunk",
            media_category=SourceMedium.BROADCAST,
            publication_form=PublicationForm.TELEVISION,
            language="de",
            url="https://www.deutschlandfunk.de/",
            is_primary=False,
        ),
    )

    report = LegacySourceIdentityReconciler(
        specs=[_spec()]
    ).reconcile(db)

    assert report.has_conflicts is True
    assert "differs from canonical" in report.conflicts[0]


def test_legacy_identity_missing_source_is_conflict(db) -> None:
    report = LegacySourceIdentityReconciler(
        specs=[_spec()]
    ).reconcile(db)

    assert report.has_conflicts is True
    assert report.change_count == 0
    assert "expected legacy Source is missing" in report.conflicts[0]



def test_default_legacy_identity_specs_include_zdfheute() -> None:
    spec = next(
        item
        for item in LEGACY_SOURCE_IDENTITY_SPECS
        if item.legacy_slug == "zdfheute"
    )

    assert spec.canonical_name == "ZDF"
    assert spec.canonical_url == "https://www.zdf.de/nachrichten/"
    assert [outlet.name for outlet in spec.outlets] == [
        "ZDFheute",
        "ZDF Nachrichten",
    ]
    assert spec.outlets[0].media_category == SourceMedium.DIGITAL
    assert spec.outlets[0].is_primary is True
    assert spec.outlets[1].media_category == SourceMedium.BROADCAST
    assert spec.outlets[1].publication_form == PublicationForm.TELEVISION
