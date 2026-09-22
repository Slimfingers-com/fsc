import json
import logging
import re
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.responses import Response


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
    status_code = 500

    try:
        response = await call_next(
            request
        )
        status_code = (
            response.status_code
        )
        response.headers[
            "X-Request-ID"
        ] = request_id
        security_headers(response)
        return response
    finally:
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
                    "status": status_code,
                    "duration_ms": round(
                        duration_ms,
                        2,
                    ),
                },
                separators=(",", ":"),
            )
        )
        request_id_context.reset(
            token
        )
