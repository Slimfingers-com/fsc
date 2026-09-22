import json
from uuid import UUID


def test_request_id_and_security_headers(
    client,
):
    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "test-request-123",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["X-Request-ID"]
        == "test-request-123"
    )
    assert (
        response.headers[
            "X-Content-Type-Options"
        ]
        == "nosniff"
    )
    assert (
        response.headers[
            "X-Frame-Options"
        ]
        == "DENY"
    )
    assert (
        response.headers[
            "Referrer-Policy"
        ]
        == "no-referrer"
    )
    assert "geolocation=()" in (
        response.headers[
            "Permissions-Policy"
        ]
    )


def test_invalid_request_id_is_replaced(
    client,
):
    response = client.get(
        "/health",
        headers={
            "X-Request-ID": (
                "contains spaces and "
                "must not enter logs"
            ),
        },
    )

    assert response.status_code == 200
    generated = response.headers[
        "X-Request-ID"
    ]
    UUID(generated)


def test_request_log_is_structured(
    client,
    caplog,
):
    caplog.set_level(
        "INFO",
        logger="app.http",
    )

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "log-test",
        },
    )

    assert response.status_code == 200
    records = [
        record
        for record in caplog.records
        if record.name == "app.http"
    ]
    assert records

    payload = json.loads(
        records[-1].message
    )
    assert payload[
        "event"
    ] == "http_request"
    assert payload[
        "request_id"
    ] == "log-test"
    assert payload[
        "method"
    ] == "GET"
    assert payload[
        "path"
    ] == "/health"
    assert payload[
        "status"
    ] == 200
    assert payload[
        "duration_ms"
    ] >= 0


def test_liveness_and_readiness(
    client,
):
    live = client.get(
        "/health/live"
    )
    ready = client.get(
        "/health/ready"
    )

    assert live.status_code == 200
    assert live.json() == {
        "status": "ok",
    }
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "ready",
        "database": "connected",
    }
