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
