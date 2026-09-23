from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums.source_metadata import (
    SourceClassificationDimension,
    SourceClassifierType,
    SourceMetricKind,
)
from app.enums.source_type import SourceType
from app.models.source_metadata import SourceClassification, SourceMetric, SourceOutlet
from app.schemas.source import SourceCreate
from app.services.source import SourceService


def make_source(db):
    return SourceService().create_source(
        db,
        SourceCreate(
            name="Metadata Test Source",
            url="https://metadata.example.com",
            source_type=SourceType.NEWS,
        ),
    )


def test_source_outlet_rejects_invalid_media_category(db):
    source = make_source(db)
    db.add(
        SourceOutlet(
            source_id=source.id,
            name="Invalid outlet",
            normalized_name="invalid outlet",
            media_category="invalid",
            publication_form="magazine",
            active=True,
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_source_classification_rejects_invalid_dimension(db):
    source = make_source(db)
    db.add(
        SourceClassification(
            source_id=source.id,
            dimension="invalid",
            value="test",
            classifier_type=SourceClassifierType.ACADEMIC,
            classifier_name="Research Institute",
            source_url="https://example.com/classification",
            reference_date=date(2026, 9, 22),
            retrieved_at=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_source_classification_rejects_invalid_validity_range(db):
    source = make_source(db)
    db.add(
        SourceClassification(
            source_id=source.id,
            dimension=SourceClassificationDimension.EDITORIAL_ORIENTATION,
            value="example",
            classifier_type=SourceClassifierType.MEDIA_DATABASE,
            classifier_name="Example Database",
            source_url="https://example.com/classification",
            reference_date=date(2026, 9, 22),
            valid_from=date(2026, 9, 22),
            valid_to=date(2026, 9, 21),
            retrieved_at=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_source_metric_rejects_negative_value(db):
    source = make_source(db)
    db.add(
        SourceMetric(
            source_id=source.id,
            metric_kind=SourceMetricKind.SOLD_CIRCULATION,
            value=-1,
            unit="count",
            metric_scope="source_total",
            reference_period="Q2/2026",
            measurement_body="IVW",
            source_url="https://example.com/metric",
            audited=True,
            retrieved_at=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_source_metric_rejects_invalid_period_range(db):
    source = make_source(db)
    db.add(
        SourceMetric(
            source_id=source.id,
            metric_kind=SourceMetricKind.PRINT_RUN,
            value=1000,
            unit="count",
            metric_scope="source_total",
            reference_period="Q2/2026",
            period_start=date(2026, 6, 30),
            period_end=date(2026, 4, 1),
            measurement_body="Publisher",
            source_url="https://example.com/metric",
            audited=False,
            retrieved_at=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()



def test_source_metric_uniqueness_is_scoped_by_outlet(db):
    source = make_source(db)
    first_outlet = SourceOutlet(
        source_id=source.id,
        name="Daily",
        normalized_name="daily",
        media_category="print",
        publication_form="daily_newspaper",
        active=True,
    )
    second_outlet = SourceOutlet(
        source_id=source.id,
        name="Sunday",
        normalized_name="sunday",
        media_category="print",
        publication_form="sunday_newspaper",
        active=True,
    )
    db.add_all([first_outlet, second_outlet])
    db.flush()

    common = {
        "source_id": source.id,
        "metric_kind": SourceMetricKind.SOLD_CIRCULATION,
        "value": 1000,
        "unit": "count",
        "metric_scope": "print_total",
        "reference_period": "Q2/2026",
        "measurement_body": "IVW",
        "source_url": "https://example.com/metric",
        "audited": True,
        "retrieved_at": datetime.now(UTC),
    }
    db.add(SourceMetric(outlet_id=first_outlet.id, **common))
    db.add(SourceMetric(outlet_id=second_outlet.id, **common))
    db.flush()


def test_duplicate_source_wide_metric_is_rejected(db):
    source = make_source(db)
    common = {
        "source_id": source.id,
        "outlet_id": None,
        "metric_kind": SourceMetricKind.SUBSCRIBERS,
        "value": 1000,
        "unit": "count",
        "metric_scope": "source_total",
        "reference_period": "2026",
        "measurement_body": "Publisher",
        "source_url": "https://example.com/metric",
        "audited": False,
        "retrieved_at": datetime.now(UTC),
    }
    db.add(SourceMetric(**common))
    db.flush()
    db.add(SourceMetric(**common))

    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize(
    ("metric_kind", "value", "unit"),
    [
        (SourceMetricKind.RADIO_DAILY_LISTENERS, 2_248_000, "listeners"),
        (SourceMetricKind.RADIO_HOURLY_LISTENERS, 420_000, "listeners"),
        (SourceMetricKind.RADIO_MARKET_SHARE, 1250, "basis_points"),
        (SourceMetricKind.TV_VIEWERS, 1_100_000, "viewers"),
        (SourceMetricKind.TV_DAILY_REACH, 4_200_000, "viewers"),
        (SourceMetricKind.TV_MARKET_SHARE, 170, "basis_points"),
    ],
)
def test_source_metric_accepts_broadcast_metric_kinds(db, metric_kind, value, unit):
    source = make_source(db)
    db.add(
        SourceMetric(
            source_id=source.id,
            metric_kind=metric_kind,
            value=value,
            unit=unit,
            metric_scope="broadcast_total",
            reference_period="2026",
            measurement_body="Audience Measurement Body",
            source_url="https://example.com/broadcast-metric",
            audited=False,
            retrieved_at=datetime.now(UTC),
        )
    )
    db.flush()


def test_source_metric_rejects_invalid_metric_kind(db):
    source = make_source(db)
    db.add(
        SourceMetric(
            source_id=source.id,
            metric_kind="broadcast_reach",
            value=1000,
            unit="people",
            metric_scope="broadcast_total",
            reference_period="2026",
            measurement_body="Audience Measurement Body",
            source_url="https://example.com/broadcast-metric",
            audited=False,
            retrieved_at=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()
