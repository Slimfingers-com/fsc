import pytest

from app.core.exceptions import BusinessRuleViolationError
from app.enums.confirmation_role import ConfirmationRole
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate
from app.schemas.source import SourceCreate
from app.schemas.source_metadata import SourceOutletCreate
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



def test_catalog_reconciliation_supports_news_media_catalog_defaults(db) -> None:
    catalog = {
        "catalog_version": "1.0-draft.2",
        "country": "DE",
        "language": "de",
        "media_category": "digital",
        "runtime_source_type": "NEWS",
        "runtime_coverage_scope": "NATIONAL",
        "feed_activation_policy": (
            "only_verified_relevant_official_content_channels_are_activated"
        ),
        "feed_class_policy": "catalog_review_metadata_only_not_persisted",
        "feed_role_policy": {"news": "editorial"},
        "groups": [
            {
                "key": "test",
                "entries": [
                    {
                        "key": "example-news",
                        "name": "Example News",
                        "homepage": "https://news.example/",
                        "source_action": "create_source",
                        "feeds": [
                            {
                                "name": "Latest",
                                "url": "https://news.example/feed.xml",
                                "active": True,
                                "priority": 1,
                                "fetch_interval_minutes": 30,
                                "default_confirmation_role": "editorial",
                                "feed_class": "news",
                                "activation_tier": 1,
                            }
                        ],
                        "outlets": [
                            {
                                "key": "example-news-web",
                                "name": "Example News",
                                "media_category": "digital",
                                "publication_form": "digital_native",
                                "language": "de",
                                "homepage": "https://news.example/",
                            }
                        ],
                    }
                ],
            }
        ],
    }

    report = SourceCatalogReconciler().reconcile(
        db,
        catalog,
        catalog_name="de_digital_test.json",
        apply=True,
    )

    assert report.has_conflicts is False
    source = SourceService().get_by_slug(db, "example-news")
    assert source is not None
    assert source.source_type == SourceType.NEWS
    assert source.country == "DE"
    assert source.language == "de"
    assert source.feeds[0].default_confirmation_role == ConfirmationRole.EDITORIAL


def test_catalog_reconciliation_includes_unclassified_entries(db) -> None:
    catalog = {
        "catalog_version": "1.0-draft.2",
        "country": "DE",
        "language": "de",
        "media_category": "digital",
        "runtime_source_type": "NEWS",
        "runtime_coverage_scope": "NATIONAL",
        "feed_activation_policy": (
            "only_verified_relevant_official_content_channels_are_activated"
        ),
        "feed_class_policy": "catalog_review_metadata_only_not_persisted",
        "feed_role_policy": {"news": "editorial"},
        "groups": [],
        "unclassified_entries": [
            {
                "key": "specialist",
                "name": "Specialist News",
                "homepage": "https://specialist.example/",
                "source_action": "create_source",
                "feeds": [
                    {
                        "name": "Latest",
                        "url": "https://specialist.example/feed.xml",
                        "active": True,
                        "priority": 1,
                        "fetch_interval_minutes": 30,
                        "default_confirmation_role": "editorial",
                        "feed_class": "news",
                        "activation_tier": 1,
                    }
                ],
                "outlets": [
                    {
                        "key": "specialist-web",
                        "name": "Specialist News",
                        "media_category": "digital",
                        "publication_form": "digital_native",
                        "language": "de",
                        "homepage": "https://specialist.example/",
                    }
                ],
            }
        ],
    }

    report = SourceCatalogReconciler().reconcile(
        db,
        catalog,
        catalog_name="unclassified.json",
    )

    assert report.has_conflicts is False
    assert report.change_count == 1
    assert report.actions[0].source_name == "Specialist News"



def _editorial_extension_catalog(
    *,
    include_feed: bool = False,
    include_existing_source_key: bool = True,
    outlet_url: str = "https://example.news/digital/",
) -> dict:
    feed = {
        "name": "Digital News",
        "url": "https://example.news/digital.xml",
        "active": True,
        "priority": 1,
        "fetch_interval_minutes": 30,
        "default_confirmation_role": "editorial",
        "feed_class": "news",
        "activation_tier": 1,
    }
    entry = {
        "key": "example-news-digital",
        "name": "Example News",
        "homepage": "https://example.news/",
        "source_action": "extend_existing_source",
        "feeds": [feed] if include_feed else [],
        "outlets": [
            {
                "key": "example-news-digital-web",
                "name": "Example News Digital",
                "media_category": "digital",
                "publication_form": "digital_native",
                "language": "de",
                "homepage": outlet_url,
            }
        ],
    }
    if include_existing_source_key:
        entry["existing_source_key"] = "example-news"

    return {
        "catalog_version": "1.0-draft.2",
        "country": "DE",
        "language": "de",
        "media_category": "digital",
        "runtime_source_type": "NEWS",
        "runtime_coverage_scope": "NATIONAL",
        "feed_activation_policy": (
            "only_verified_relevant_official_content_channels_are_activated"
        ),
        "feed_class_policy": "catalog_review_metadata_only_not_persisted",
        "feed_role_policy": {"news": "editorial"},
        "groups": [{"key": "test", "entries": [entry]}],
    }


def _create_editorial_base_source(db):
    return SourceService().create_source(
        db,
        SourceCreate(
            name="Example News",
            url="https://example.news/",
            source_type="NEWS",
            coverage_scope="NATIONAL",
            country="DE",
            language="de",
            outlets=[
                SourceOutletCreate(
                    name="Example News Print",
                    media_category="print",
                    publication_form="daily_newspaper",
                    language="de",
                    url="https://example.news/print/",
                    is_primary=True,
                )
            ],
        ),
    )


def test_catalog_reconciliation_extends_existing_source_without_feed(
    db,
) -> None:
    source = _create_editorial_base_source(db)
    source_id = source.id

    report = SourceCatalogReconciler().reconcile(
        db,
        _editorial_extension_catalog(),
        catalog_name="de_digital_test.json",
    )

    assert report.has_conflicts is False
    assert report.change_count == 1
    assert [action.action for action in report.actions] == [
        "create_outlet"
    ]

    SourceCatalogReconciler().reconcile(
        db,
        _editorial_extension_catalog(),
        catalog_name="de_digital_test.json",
        apply=True,
    )

    refreshed = SourceService().get_by_slug(db, source.slug)
    assert refreshed is not None
    assert refreshed.id == source_id
    assert {
        outlet.name
        for outlet in refreshed.outlets
        if outlet.deleted_at is None
    } == {
        "Example News Print",
        "Example News Digital",
    }
    primary = [
        outlet.name
        for outlet in refreshed.outlets
        if outlet.deleted_at is None and outlet.is_primary
    ]
    assert primary == ["Example News Print"]


def test_catalog_reconciliation_extension_is_idempotent(db) -> None:
    _create_editorial_base_source(db)
    reconciler = SourceCatalogReconciler()
    catalog = _editorial_extension_catalog()

    reconciler.reconcile(
        db,
        catalog,
        catalog_name="de_digital_test.json",
        apply=True,
    )
    report = reconciler.reconcile(
        db,
        catalog,
        catalog_name="de_digital_test.json",
    )

    assert report.has_conflicts is False
    assert report.change_count == 0
    assert [action.action for action in report.actions] == [
        "no_change"
    ]


def test_catalog_reconciliation_extension_can_add_reviewed_feed(db) -> None:
    source = _create_editorial_base_source(db)
    reconciler = SourceCatalogReconciler()

    report = reconciler.reconcile(
        db,
        _editorial_extension_catalog(include_feed=True),
        catalog_name="de_digital_test.json",
    )

    assert report.has_conflicts is False
    assert {action.action for action in report.actions} == {
        "create_outlet",
        "create_feed",
    }

    reconciler.reconcile(
        db,
        _editorial_extension_catalog(include_feed=True),
        catalog_name="de_digital_test.json",
        apply=True,
    )
    refreshed = SourceService().get_by_slug(db, source.slug)
    assert refreshed is not None
    assert len(refreshed.feeds) == 1
    assert refreshed.feeds[0].url == "https://example.news/digital.xml"
    assert (
        refreshed.feeds[0].default_confirmation_role
        == ConfirmationRole.EDITORIAL
    )


def test_catalog_reconciliation_feedless_extension_without_runtime_source_stays_catalog_only(
    db,
) -> None:
    report = SourceCatalogReconciler().reconcile(
        db,
        _editorial_extension_catalog(),
        catalog_name="de_digital_test.json",
    )

    assert report.has_conflicts is False
    assert report.change_count == 0
    assert report.actions == ()
    assert SourceService().get_by_slug(db, "example-news") is None


def test_catalog_reconciliation_feed_extension_requires_existing_runtime_source(
    db,
) -> None:
    report = SourceCatalogReconciler().reconcile(
        db,
        _editorial_extension_catalog(include_feed=True),
        catalog_name="de_digital_test.json",
    )

    assert report.has_conflicts is True
    assert report.change_count == 0
    assert "does not resolve to an existing runtime Source" in (
        report.conflicts[0]
    )
    assert SourceService().get_by_slug(db, "example-news") is None


def test_catalog_reconciliation_extension_requires_existing_source_key(
    db,
) -> None:
    _create_editorial_base_source(db)

    with pytest.raises(
        BusinessRuleViolationError,
        match="requires existing_source_key",
    ):
        SourceCatalogReconciler().reconcile(
            db,
            _editorial_extension_catalog(
                include_existing_source_key=False,
            ),
            catalog_name="de_digital_test.json",
        )


def test_catalog_reconciliation_extension_rejects_conflicting_outlet(
    db,
) -> None:
    source = _create_editorial_base_source(db)
    SourceService().create_outlet(
        db,
        source,
        SourceOutletCreate(
            name="Example News Digital",
            media_category="digital",
            publication_form="digital_native",
            language="de",
            url="https://different.example/",
            is_primary=False,
        ),
    )

    report = SourceCatalogReconciler().reconcile(
        db,
        _editorial_extension_catalog(),
        catalog_name="de_digital_test.json",
    )

    assert report.has_conflicts is True
    assert "differs from reviewed" in report.conflicts[0]


def test_catalog_reconciliation_still_ignores_create_source_without_feed(
    db,
) -> None:
    catalog = _editorial_extension_catalog()
    entry = catalog["groups"][0]["entries"][0]
    entry["source_action"] = "create_source"
    entry.pop("existing_source_key")

    report = SourceCatalogReconciler().reconcile(
        db,
        catalog,
        catalog_name="de_digital_test.json",
    )

    assert report.has_conflicts is False
    assert report.change_count == 0
    assert report.actions == ()
    assert SourceService().get_by_slug(db, "example-news") is None
