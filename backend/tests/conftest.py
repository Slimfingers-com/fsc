import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.settings import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


TEST_DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{settings.database_user}:"
    f"{settings.database_password}@"
    f"{settings.database_host}:"
    f"{settings.database_port}/"
    f"fsc_test"
)

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


def _truncate_database() -> None:
    table_names = ", ".join(
        f'"{table.name}"'
        for table in reversed(
            Base.metadata.sorted_tables
        )
    )

    if not table_names:
        return

    with test_engine.begin() as connection:
        connection.execute(
            text(
                f"TRUNCATE TABLE "
                f"{table_names} "
                f"RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture(autouse=True)
def clean_database():
    _truncate_database()

    yield

    _truncate_database()


@pytest.fixture()
def db(
    clean_database,
) -> Session:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode=(
            "create_savepoint"
        ),
    )

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[
        get_db
    ] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
