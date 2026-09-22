from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.exceptions import (
    BusinessRuleViolationError,
    DuplicateSourceError,
)
from app.db.session import SessionLocal
from app.core.http import (
    request_context_middleware,
)

app = FastAPI(
    title="FSC API",
    version="0.1.0",
)

app.middleware("http")(
    request_context_middleware
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


@app.exception_handler(
    BusinessRuleViolationError
)
async def business_rule_violation_exception_handler(
    request: Request,
    exc: BusinessRuleViolationError,
):
    return JSONResponse(
        status_code=422,
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



@app.get("/health/live")
def liveness():
    return {
        "status": "ok",
    }


@app.get("/health/ready")
def readiness():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "error",
            },
        )

    return {
        "status": "ready",
        "database": "connected",
    }
