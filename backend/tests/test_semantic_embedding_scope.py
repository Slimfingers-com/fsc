from types import SimpleNamespace
from uuid import uuid4

from app.semantic.provider import OpenAIEmbeddingProvider
from app.services.semantic_embedding import (
    PreparedClaimEmbedding,
    PreparedSemanticEmbedding,
    SemanticEmbeddingRunner,
    SemanticEmbeddingService,
)


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


class RecordingProvider:
    provider = "recording"
    version = "1"
    model = "recording-model"
    dimensions = 2

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(tuple(texts))
        return tuple(
            (float(index + 1), 0.0)
            for index, _ in enumerate(texts)
        )


def test_embed_batch_uses_one_provider_request_for_multiple_articles():
    provider = RecordingProvider()
    service = SemanticEmbeddingService(
        provider=provider,
        include_article_embeddings=False,
    )
    first_article_id = uuid4()
    second_article_id = uuid4()
    first_claim_id = uuid4()
    second_claim_id = uuid4()
    third_claim_id = uuid4()

    first = PreparedSemanticEmbedding(
        article_id=first_article_id,
        expected_hash="first",
        article_input_hash="first-article",
        article_text=None,
        claims=(
            PreparedClaimEmbedding(
                claim_id=first_claim_id,
                input_hash="first-claim",
                text="First claim",
            ),
        ),
    )
    second = PreparedSemanticEmbedding(
        article_id=second_article_id,
        expected_hash="second",
        article_input_hash="second-article",
        article_text=None,
        claims=(
            PreparedClaimEmbedding(
                claim_id=second_claim_id,
                input_hash="second-claim",
                text="Second claim",
            ),
            PreparedClaimEmbedding(
                claim_id=third_claim_id,
                input_hash="third-claim",
                text="Third claim",
            ),
        ),
    )

    result = service.embed_batch((first, second))

    assert provider.calls == [
        ("First claim", "Second claim", "Third claim")
    ]
    assert result[first_article_id][0] is None
    assert result[first_article_id][1] == {
        first_claim_id: (1.0, 0.0),
    }
    assert result[second_article_id][0] is None
    assert result[second_article_id][1] == {
        second_claim_id: (2.0, 0.0),
        third_claim_id: (3.0, 0.0),
    }


def test_runner_batch_budget_defers_whole_articles():
    service = SemanticEmbeddingService(
        provider=FakeProvider(),
        include_article_embeddings=False,
    )
    runner = SemanticEmbeddingRunner(
        lambda: None,
        service,
        max_batch_characters=12,
    )

    first = PreparedSemanticEmbedding(
        article_id=uuid4(),
        expected_hash="first",
        article_input_hash="first-article",
        article_text=None,
        claims=(
            PreparedClaimEmbedding(
                claim_id=uuid4(),
                input_hash="first-claim",
                text="12345678",
            ),
        ),
    )
    second = PreparedSemanticEmbedding(
        article_id=uuid4(),
        expected_hash="second",
        article_input_hash="second-article",
        article_text=None,
        claims=(
            PreparedClaimEmbedding(
                claim_id=uuid4(),
                input_hash="second-claim",
                text="12345",
            ),
        ),
    )

    selected, deferred = runner._bounded_batch(
        [
            (object(), first),
            (object(), second),
        ]
    )

    assert [item[1].article_id for item in selected] == [
        first.article_id
    ]
    assert [item[1].article_id for item in deferred] == [
        second.article_id
    ]


def test_runner_batch_budget_allows_oversized_first_article():
    service = SemanticEmbeddingService(
        provider=FakeProvider(),
        include_article_embeddings=False,
    )
    runner = SemanticEmbeddingRunner(
        lambda: None,
        service,
        max_batch_characters=4,
    )
    oversized = PreparedSemanticEmbedding(
        article_id=uuid4(),
        expected_hash="oversized",
        article_input_hash="oversized-article",
        article_text=None,
        claims=(
            PreparedClaimEmbedding(
                claim_id=uuid4(),
                input_hash="oversized-claim",
                text="12345678",
            ),
        ),
    )
    next_item = PreparedSemanticEmbedding(
        article_id=uuid4(),
        expected_hash="next",
        article_input_hash="next-article",
        article_text=None,
        claims=(
            PreparedClaimEmbedding(
                claim_id=uuid4(),
                input_hash="next-claim",
                text="1",
            ),
        ),
    )

    selected, deferred = runner._bounded_batch(
        [
            (object(), oversized),
            (object(), next_item),
        ]
    )

    assert [item[1].article_id for item in selected] == [
        oversized.article_id
    ]
    assert [item[1].article_id for item in deferred] == [
        next_item.article_id
    ]
