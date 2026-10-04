from types import SimpleNamespace
from uuid import uuid4

from app.semantic.provider import OpenAIEmbeddingProvider
from app.services.semantic_embedding import SemanticEmbeddingService


class FakeProvider:
    provider = "fake"
    version = "1"
    model = "fake-model"

    def embed(self, texts):
        return tuple((1.0, 0.0) for _ in texts)


def test_claim_only_service_does_not_prepare_article_embedding():
    service = SemanticEmbeddingService(
        provider=FakeProvider(),
        include_article_embeddings=False,
    )
    article = SimpleNamespace(
        id=uuid4(),
        content_hash="article-hash",
        language_code="en",
        normalized_title="Title",
        title="Title",
        normalized_text="Body text",
        semantic_embedding=None,
        semantic_model=None,
        semantic_input_hash=None,
    )
    claim = SimpleNamespace(
        id=uuid4(),
        claim_hash="claim-hash",
        claim_text="A factual claim.",
        semantic_embedding=None,
        semantic_model=None,
        semantic_input_hash=None,
    )

    prepared = service.prepare(article, (claim,))

    assert prepared.article_text is None
    assert len(prepared.claims) == 1
    assert prepared.claims[0].claim_id == claim.id



def test_dimension_change_marks_existing_claim_embedding_stale():
    provider = FakeProvider()
    provider.dimensions = 3
    service = SemanticEmbeddingService(
        provider=provider,
        include_article_embeddings=False,
    )
    article = SimpleNamespace(
        id=uuid4(),
        content_hash="article-hash",
        language_code="en",
        normalized_title="Title",
        title="Title",
        normalized_text="Body text",
        semantic_embedding=None,
        semantic_model=None,
        semantic_input_hash=None,
    )
    claim = SimpleNamespace(
        id=uuid4(),
        claim_hash="claim-hash",
        claim_text="A factual claim.",
        semantic_embedding=[1.0, 0.0],
        semantic_model="fake-model",
        semantic_input_hash="claim-hash",
    )

    prepared = service.prepare(article, (claim,))

    assert [item.claim_id for item in prepared.claims] == [claim.id]


def test_openai_provider_sends_requested_dimensions(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {"index": 0, "embedding": [1.0, 0.0, 0.0]},
                ]
            }

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return Response()

    monkeypatch.setattr("app.semantic.provider.httpx.post", fake_post)

    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimensions=3,
    )
    result = provider.embed(("claim",))

    assert result == ((1.0, 0.0, 0.0),)
    assert captured["json"]["dimensions"] == 3


def test_openai_provider_omits_dimensions_by_default(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            }

    def fake_post(url, *, headers, json, timeout):
        captured["json"] = json
        return Response()

    monkeypatch.setattr("app.semantic.provider.httpx.post", fake_post)

    provider = OpenAIEmbeddingProvider(api_key="test-key")
    provider.embed(("claim",))

    assert "dimensions" not in captured["json"]
