from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import SessionLocal

app = FastAPI(
    title="FSC API",
    version="0.1.0",
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
