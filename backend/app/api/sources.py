from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.source import SourceCreate, SourceRead
from app.services.source import SourceService

router = APIRouter(
    prefix="/sources",
    tags=["sources"],
)

service = SourceService()


@router.get(
    "/{slug}",
    response_model=SourceRead,
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
):
    source = service.create_source(
        db=db,
        data=data,
    )

    db.commit()
    db.refresh(source)

    return source
