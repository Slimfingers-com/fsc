from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.schemas.source import SourceCreate, SourceDetailRead, SourceRead
from app.schemas.source_metadata import (
    SourceClassificationCreate,
    SourceClassificationRead,
    SourceMetricCreate,
    SourceMetricRead,
)
from app.services.source import SourceService

router = APIRouter(
    prefix="/sources",
    tags=["sources"],
)

service = SourceService()


def require_source_admin(
    x_fsc_admin_key: Annotated[
        str | None,
        Header(alias="X-FSC-Admin-Key"),
    ] = None,
) -> None:
    expected = settings.source_admin_api_key

    if not expected:
        raise HTTPException(
            status_code=503,
            detail=(
                "Source administration is not configured."
            ),
        )

    if (
        x_fsc_admin_key is None
        or not compare_digest(
            x_fsc_admin_key,
            expected,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid or missing source admin API key."
            ),
        )


@router.get(
    "/{slug}",
    response_model=SourceDetailRead,
)
def get_source(
    slug: str,
    db: Session = Depends(get_db),
):
    source = service.get_by_slug(db, slug)

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Source not found.",
        )

    return source


@router.get(
    "",
    response_model=list[SourceRead],
)
def list_sources(
    db: Session = Depends(get_db),
):
    return service.list_active(db)


@router.post(
    "",
    response_model=SourceRead,
    status_code=201,
)
def create_source(
    data: SourceCreate,
    db: Session = Depends(get_db),
    _admin: None = Depends(
        require_source_admin
    ),
):
    source = service.create_source(
        db=db,
        data=data,
    )

    db.commit()
    db.refresh(source)

    return source


@router.post(
    "/{slug}/classifications",
    response_model=SourceClassificationRead,
    status_code=201,
)
def create_source_classification(
    slug: str,
    data: SourceClassificationCreate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_source_admin),
):
    source = service.get_by_slug(db, slug)

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Source not found.",
        )

    classification = service.create_classification(
        db,
        source,
        data,
    )
    db.commit()
    db.refresh(classification)
    return classification


@router.post(
    "/{slug}/metrics",
    response_model=SourceMetricRead,
    status_code=201,
)
def create_source_metric(
    slug: str,
    data: SourceMetricCreate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_source_admin),
):
    source = service.get_by_slug(db, slug)

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Source not found.",
        )

    metric = service.create_metric(
        db,
        source,
        data,
    )
    db.commit()
    db.refresh(metric)
    return metric
