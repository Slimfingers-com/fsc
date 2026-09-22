from datetime import date

import pytest
from pydantic import ValidationError

from app.enums.media_family import MediaFamily
from app.enums.publication_format import PublicationFormat
from app.enums.publication_frequency import PublicationFrequency
from app.enums.reach_metric_quality import ReachMetricQuality
from app.enums.reach_metric_type import ReachMetricType
from app.enums.source_classification import SourceClassificationKind
from app.enums.source_type import SourceType
from app.schemas.source import (
    SourceClassificationCreate,
    SourceCreate,
    SourceReachMetricCreate,
)
from app.services.source import SourceService


def test_source_metadata_round_trip(db):
    service = SourceService()
    source = service.create_source(
        db,
        SourceCreate(
            name="Example Weekly",
            url="https://example.test",
            source_type=SourceType.NEWS,
            country="ch",
            language="de",
            content_languages=["DE", "en", "de"],
            media_family=MediaFamily.PRINT,
            publication_format=PublicationFormat.WEEKLY_NEWSPAPER,
            publication_frequency=PublicationFrequency.WEEKLY,
            coverage_countries=["de", "AT", "de"],
            classifications=[
                SourceClassificationCreate(
                    kind=SourceClassificationKind.POLITICAL_ORIENTATION,
                    value="CENTER_RIGHT",
                    detail="liberal-konservativ",
                    evidence_source_name="Example Research",
                    evidence_url="https://research.example.test/source",
                    as_of=date(2026, 9, 1),
                ),
                SourceClassificationCreate(
                    kind=SourceClassificationKind.RADICALITY,
                    value="MAINSTREAM",
                    evidence_source_name="Example Research",
                    as_of=date(2026, 9, 1),
                ),
            ],
            reach_metrics=[
                SourceReachMetricCreate(
                    metric_type=ReachMetricType.PRINT_SOLD_CIRCULATION,
                    metric_value=123456,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 6, 30),
                    evidence_source_name="IVW",
                    evidence_url="https://ivw.example.test",
                    quality=ReachMetricQuality.AUDITED,
                )
            ],
        ),
    )
    db.flush()

    loaded = service.get_by_slug(db, source.slug)
    assert loaded is not None
    assert loaded.country == "CH"
    assert loaded.language == "de"
    assert loaded.content_languages == ["de", "en"]
    assert loaded.media_family == MediaFamily.PRINT
    assert loaded.publication_format == PublicationFormat.WEEKLY_NEWSPAPER
    assert loaded.publication_frequency == PublicationFrequency.WEEKLY
    assert loaded.coverage_countries == ["DE", "AT"]
    assert len(loaded.classifications) == 2
    assert loaded.classifications[0].evidence_source_name == "Example Research"
    assert len(loaded.reach_metrics) == 1
    assert loaded.reach_metrics[0].metric_value == 123456
    assert loaded.reach_metrics[0].quality == ReachMetricQuality.AUDITED


def test_rejects_unknown_classification_value():
    with pytest.raises(ValidationError):
        SourceClassificationCreate(
            kind=SourceClassificationKind.POLITICAL_ORIENTATION,
            value="WHATEVER",
            evidence_source_name="Research",
        )


def test_rejects_multiple_primary_classifications_of_same_kind():
    with pytest.raises(ValidationError):
        SourceCreate(
            name="Invalid",
            url="https://invalid.example.test",
            source_type=SourceType.NEWS,
            classifications=[
                SourceClassificationCreate(
                    kind=SourceClassificationKind.POLITICAL_ORIENTATION,
                    value="LEFT",
                    evidence_source_name="A",
                ),
                SourceClassificationCreate(
                    kind=SourceClassificationKind.POLITICAL_ORIENTATION,
                    value="CENTER_LEFT",
                    evidence_source_name="B",
                ),
            ],
        )


def test_rejects_reverse_reach_period():
    with pytest.raises(ValidationError):
        SourceReachMetricCreate(
            metric_type=ReachMetricType.DIGITAL_VISITS,
            metric_value=42,
            period_start=date(2026, 9, 2),
            period_end=date(2026, 9, 1),
            evidence_source_name="Publisher",
        )


def test_rejects_invalid_source_country_code():
    with pytest.raises(ValidationError):
        SourceCreate(
            name="Invalid Country",
            url="https://invalid-country.example.test",
            source_type=SourceType.NEWS,
            country="D1",
        )

