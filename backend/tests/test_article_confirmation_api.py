from uuid import uuid4

import pytest

from app.core.settings import settings
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.confirmation_role import ConfirmationRole
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.feed import Feed
from app.schemas.source import SourceCreate
from app.services.source import SourceService


ADMIN_KEY = "test-source-admin-key"
ADMIN_HEADERS = {
    "X-FSC-Admin-Key": ADMIN_KEY,
}


@pytest.fixture(autouse=True)
def configure_source_admin_key(monkeypatch):
    monkeypatch.setattr(
        settings,
        "source_admin_api_key",
        ADMIN_KEY,
    )


def make_article(db):
    source = SourceService().create_source(
        db,
        SourceCreate(
            name=f"Confirmation {uuid4().hex}",
            url=f"https://{uuid4().hex}.example.com",
            source_type=SourceType.NEWS,
        ),
    )
    feed = Feed(
        source=source,
        name="Main",
        url=f"https://{uuid4().hex}.example.com/feed.xml",
    )
    article = Article(
        feed=feed,
        identity_type=ArticleIdentityType.DERIVED,
        identity_key=uuid4().hex * 2,
        title="Confirmation role article",
    )
    db.add(article)
    db.flush()
    return article


def test_article_confirmation_role_round_trip(client, db):
    article = make_article(db)
    db.commit()

    initial = client.get(
        f"/articles/{article.id}/confirmation-role"
    )
    assert initial.status_code == 200
    assert initial.json() == {
        "article_id": str(article.id),
        "confirmation_role": "editorial",
    }

    response = client.patch(
        f"/articles/{article.id}/confirmation-role",
        headers=ADMIN_HEADERS,
        json={
            "confirmation_role": "expert_analysis",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "article_id": str(article.id),
        "confirmation_role": "expert_analysis",
    }

    db.refresh(article)
    assert article.confirmation_role is ConfirmationRole.EXPERT_ANALYSIS


def test_article_confirmation_role_update_requires_admin(client, db):
    article = make_article(db)
    db.commit()

    response = client.patch(
        f"/articles/{article.id}/confirmation-role",
        json={
            "confirmation_role": "advocacy",
        },
    )
    assert response.status_code == 401


def test_article_confirmation_role_rejects_unknown_role(client, db):
    article = make_article(db)
    db.commit()

    response = client.patch(
        f"/articles/{article.id}/confirmation-role",
        headers=ADMIN_HEADERS,
        json={
            "confirmation_role": "independent_because_i_say_so",
        },
    )
    assert response.status_code == 422
