import pytest

from app.core.exceptions import BusinessRuleViolationError
from app.enums.confirmation_role import ConfirmationRole
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate
from app.schemas.source import SourceCreate
from app.services.source import SourceService
from app.services.source_catalog_reconciliation import (
    SourceCatalogReconciler,
)


def _catalog(
    *,
    source_type: str = "ACADEMIC",
    source_name: str = "Example Institute",
    source_key: str = "example-institute",
    country: str = "DE",
    feed_name: str = "Research",
    feed_url: str = "https://example.org/research.xml",
    feed_active: bool = True,
    feed_priority: int = 1,
    feed_interval: int = 60,
    feed_role: str = "expert_analysis",
    feed_class: str = "research_publication",
    activation_tier: int = 1,
) -> dict:
    independent_policy = {
        "research_publication": "expert_analysis",
        "official_data": "primary_evidence",
        "press_release": "primary_evidence",
        "news": "primary_evidence",
        "position_statement": "advocacy",
        "signal": "signal",
    }
    interest_policy = {
        **independent_policy,
        "research_publication": "advocacy",
    }
    policy = (
        independent_policy
        if source_type in {"ACADEMIC", "THINK_TANK"}
        else interest_policy
    )
    return {
        "catalog_version": "1.0-draft.2",
        "country": country,
        "language": "de" if country == "DE" else "en",
        "organization_type": source_type,
        "feed_activation_policy": (
            "only_verified_relevant_official_content_channels_are_activated"
        ),
        "feed_class_policy": "catalog_review_metadata_only_not_persisted",
        "feed_role_policy": policy,
        "groups": [
            {
                "key": "test",
                "entries": [
                    {
                        "key": source_key,
                        "name": source_name,
                        "homepage": "https://example.org/",
                        "source_action": "create_source",
                        "source_type": source_type,
                        "country": country,
                        "language": (
                            "de" if country == "DE" else "en"
                        ),
                        "feeds": [
                            {
                                "name": feed_name,
                                "url": feed_url,
                                "active": feed_active,
                                "priority": feed_priority,
                                "fetch_interval_minutes": feed_interval,
                                "default_confirmation_role": feed_role,
                                "feed_class": feed_class,
                                "activation_tier": activation_tier,
                            }
                        ],
                        "outlets": [
                            {
                                "key": f"{source_key}-official",
                                "name": source_name,
                                "media_category": "organization",
                                "publication_form": "other",
                                "language": (
                                    "de" if country == "DE" else "en"
                                ),
                                "homepage": "https://example.org/",
                            }
                        ],
                    },
                    {
                        "key": "catalog-only",
                        "name": "Catalog Only Organization",
                        "homepage": "https://catalog-only.example/",
                        "source_action": "create_source",
                        "source_type": source_type,
                        "country": country,
                        "language": (
                            "de" if country == "DE" else "en"
                        ),
                        "feeds": [],
                        "outlets": [],
                    },
                ],
            }
        ],
    }


def test_catalog_reconciliation_dry_run_only_plans_reviewed_feed_entries(
    db,
) -> None:
    reconciler = SourceCatalogReconciler()

    report = reconciler.reconcile(
        db,
        _catalog(),
        catalog_name="test.json",
    )

    assert report.has_conflicts is False
    assert report.change_count == 1
    assert report.actions[0].action == "create_source"
    assert report.actions[0].source_name == "Example Institute"
    assert (
        reconciler.source_service.repository.get_by_normalized_name(
            db,
            "example institute",
        )
        is None
    )
    assert (
        reconciler.source_service.repository.get_by_normalized_name(
            db,
            "catalog only organization",
        )
        is None
    )


def test_catalog_reconciliation_apply_creates_source_feed_and_primary_outlet(
    db,
) -> None:
    reconciler = SourceCatalogReconciler()

    report = reconciler.reconcile(
        db,
        _catalog(),
        catalog_name="test.json",
        apply=True,
    )

    assert report.change_count == 1
    source = reconciler.source_service.repository.get_by_normalized_name(
        db,
        "example institute",
    )
    assert source is not None
    assert source.source_type == SourceType.ACADEMIC
    assert source.country == "DE"
    assert len(source.feeds) == 1
    feed = source.feeds[0]
    assert feed.name == "Research"
    assert feed.active is True
    assert feed.priority == 1
    assert feed.fetch_interval_minutes == 60
    assert (
        feed.default_confirmation_role
        == ConfirmationRole.EXPERT_ANALYSIS
    )
    assert len(source.outlets) == 1
    assert source.outlets[0].is_primary is True

    assert (
        reconciler.source_service.repository.get_by_normalized_name(
            db,
            "catalog only organization",
        )
        is None
    )


def test_catalog_reconciliation_is_idempotent(
    db,
) -> None:
    reconciler = SourceCatalogReconciler()
    catalog = _catalog()

    reconciler.reconcile(
        db,
        catalog,
        catalog_name="test.json",
        apply=True,
    )
    report = reconciler.reconcile(
        db,
        catalog,
        catalog_name="test.json",
    )

    assert report.has_conflicts is False
    assert report.change_count == 0
    assert [action.action for action in report.actions] == [
        "no_change"
    ]


def test_catalog_reconciliation_updates_existing_feed_runtime_fields(
    db,
) -> None:
    reconciler = SourceCatalogReconciler()
    catalog = _catalog()

    reconciler.reconcile(
        db,
        catalog,
        catalog_name="test.json",
        apply=True,
    )
    updated = _catalog(
        feed_name="Research updates",
        feed_active=False,
        feed_priority=2,
        feed_interval=120,
        activation_tier=2,
    )

    report = reconciler.reconcile(
        db,
        updated,
        catalog_name="test.json",
    )
    assert report.change_count == 1
    assert report.actions[0].action == "update_feed"

    reconciler.reconcile(
        db,
        updated,
        catalog_name="test.json",
        apply=True,
    )
    source = reconciler.source_service.repository.get_by_normalized_name(
        db,
        "example institute",
    )
    feed = source.feeds[0]
    assert feed.name == "Research updates"
    assert feed.active is False
    assert feed.priority == 2
    assert feed.fetch_interval_minutes == 120


def test_catalog_reconciliation_does_not_delete_unmanaged_runtime_feeds(
    db,
) -> None:
    reconciler = SourceCatalogReconciler()
    catalog = _catalog()
    reconciler.reconcile(
        db,
        catalog,
        catalog_name="test.json",
        apply=True,
    )
    source = reconciler.source_service.repository.get_by_normalized_name(
        db,
        "example institute",
    )
    reconciler.source_service.create_feed(
        db,
        source,
        FeedCreate(
            name="Manual feed",
            url="https://example.org/manual.xml",
            active=False,
            priority=3,
            fetch_interval_minutes=180,
        ),
    )

    reconciler.reconcile(
        db,
        catalog,
        catalog_name="test.json",
        apply=True,
    )
    db.expire(source, ["feeds"])

    refreshed = reconciler.source_service.get_by_slug(
        db,
        source.slug,
    )
    assert refreshed is not None
    assert {
        feed.url
        for feed in refreshed.feeds
        if feed.deleted_at is None
    } == {
        "https://example.org/research.xml",
        "https://example.org/manual.xml",
    }


def test_catalog_reconciliation_reports_source_identity_conflict(
    db,
) -> None:
    service = SourceService()
    service.create_source(
        db,
        SourceCreate(
            name="Example Institute",
            url="https://example.org/",
            source_type="COMPANY",
            country="DE",
            language="de",
        ),
    )
    reconciler = SourceCatalogReconciler(service)

    report = reconciler.reconcile(
        db,
        _catalog(),
        catalog_name="test.json",
    )

    assert report.has_conflicts is True
    assert "SourceType" in report.conflicts[0]

    with pytest.raises(BusinessRuleViolationError):
        reconciler.reconcile(
            db,
            _catalog(),
            catalog_name="test.json",
            apply=True,
        )


def test_catalog_reconciliation_reports_feed_name_url_conflict(
    db,
) -> None:
    service = SourceService()
    source = service.create_source(
        db,
        SourceCreate(
            name="Example Institute",
            url="https://example.org/",
            source_type="ACADEMIC",
            country="DE",
            language="de",
            feeds=[
                FeedCreate(
                    name="Research",
                    url="https://example.org/old.xml",
                    active=True,
                    priority=1,
                    fetch_interval_minutes=60,
                    default_confirmation_role="expert_analysis",
                )
            ],
        ),
    )
    assert source is not None
    reconciler = SourceCatalogReconciler(service)

    report = reconciler.reconcile(
        db,
        _catalog(),
        catalog_name="test.json",
    )

    assert report.has_conflicts is True
    assert "already exists with URL" in report.conflicts[0]


def test_catalog_reconciliation_reports_feed_url_owned_by_other_source(
    db,
) -> None:
    service = SourceService()
    service.create_source(
        db,
        SourceCreate(
            name="Other Institute",
            url="https://other.example/",
            source_type="ACADEMIC",
            country="DE",
            language="de",
            feeds=[
                FeedCreate(
                    name="Research",
                    url="https://example.org/research.xml",
                    active=True,
                    priority=1,
                    fetch_interval_minutes=60,
                    default_confirmation_role="expert_analysis",
                )
            ],
        ),
    )
    reconciler = SourceCatalogReconciler(service)

    report = reconciler.reconcile(
        db,
        _catalog(),
        catalog_name="test.json",
    )

    assert report.has_conflicts is True
    assert "already belongs to a runtime Source" in report.conflicts[0]


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda catalog: catalog.update(
                {"feed_activation_policy": "catalog_only"}
            ),
            "not marked as reviewed",
        ),
        (
            lambda catalog: catalog["groups"][0]["entries"][0][
                "feeds"
            ][0].update(
                {"default_confirmation_role": "primary_evidence"}
            ),
            "feed role does not match",
        ),
        (
            lambda catalog: catalog["groups"][0]["entries"][0][
                "feeds"
            ][0].update({"active": False}),
            "active flag does not match",
        ),
    ],
)
def test_catalog_reconciliation_rejects_unreviewed_or_inconsistent_catalogs(
    db,
    mutator,
    message,
) -> None:
    catalog = _catalog()
    mutator(catalog)

    with pytest.raises(
        BusinessRuleViolationError,
        match=message,
    ):
        SourceCatalogReconciler().reconcile(
            db,
            catalog,
            catalog_name="test.json",
        )
