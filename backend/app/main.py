from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.exceptions import DuplicateSourceError
from app.db.session import SessionLocal

app = FastAPI(
    title="FSC API",
    version="0.1.0",
)

app.include_router(api_router)


@app.exception_handler(DuplicateSourceError)
async def duplicate_source_exception_handler(
    request: Request,
    exc: DuplicateSourceError,
):
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
        },
    )


@app.get("/health")
def health():
    database_status = "disconnected"

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "error"

    return {
        "status": "ok",
        "database": database_status,
    }
