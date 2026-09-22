import json
import logging
import re
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.responses import JSONResponse, Response


logger = logging.getLogger("app.http")

_REQUEST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]{1,128}$"
)
request_id_context: ContextVar[str | None] = (
    ContextVar(
        "request_id",
        default=None,
    )
)


def normalize_request_id(
    value: str | None,
) -> str:
    if (
        value is not None
        and _REQUEST_ID_PATTERN.fullmatch(
            value
        )
    ):
        return value
    return str(uuid4())


def security_headers(
    response: Response,
) -> None:
    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"
    response.headers[
        "X-Frame-Options"
    ] = "DENY"
    response.headers[
        "Referrer-Policy"
    ] = "no-referrer"
    response.headers[
        "Permissions-Policy"
    ] = (
        "camera=(), microphone=(), "
        "geolocation=()"
    )


async def request_context_middleware(
    request: Request,
    call_next,
):
    request_id = normalize_request_id(
        request.headers.get(
            "X-Request-ID"
        )
    )
    token = request_id_context.set(
        request_id
    )
    request.state.request_id = request_id
    started = perf_counter()

    try:
        try:
            response = await call_next(
                request
            )
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": (
                            "http_unhandled_exception"
                        ),
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": (
                            type(exc).__name__
                        ),
                    },
                    separators=(",", ":"),
                )
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": (
                        "Internal server error."
                    ),
                    "request_id": request_id,
                },
            )

        response.headers[
            "X-Request-ID"
        ] = request_id
        security_headers(response)

        duration_ms = (
            perf_counter() - started
        ) * 1000
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": (
                        response.status_code
                    ),
                    "duration_ms": round(
                        duration_ms,
                        2,
                    ),
                },
                separators=(",", ":"),
            )
        )
        return response
    finally:
        request_id_context.reset(
            token
        )
