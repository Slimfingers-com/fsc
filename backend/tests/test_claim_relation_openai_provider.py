from uuid import uuid4

import httpx
import pytest

from app.claim_relations.openai_provider import (
    OpenAISemanticClaimRelationProvider,
)
from app.claim_relations.provider import (
    SemanticRelationCandidate,
    SemanticRelationKind,
    StoryClaimInput,
)


class FakeResponse:
    def __init__(
        self,
        payload,
        *,
        status_code=200,
        headers=None,
    ):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code < 400:
            return None
        request = httpx.Request(
            "POST",
            "https://api.openai.com/v1/responses",
        )
        response = httpx.Response(
            self.status_code,
            request=request,
            json=self.payload,
            headers=self.headers,
        )
        raise httpx.HTTPStatusError(
            f"HTTP {self.status_code}",
            request=request,
            response=response,
        )

    def json(self):
        return self.payload


def make_claim(text):
    return StoryClaimInput(
        claim_id=uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text=text,
        normalized_claim=text.casefold().rstrip("."),
        claim_hash=uuid4().hex * 2,
        confidence=0.9,
        article_title="ICE vehicle collision",
        article_context=(
            "ICE vehicle collision\n\n"
            + text
        ),
    )


def make_candidate():
    return SemanticRelationCandidate(
        story_id=uuid4(),
        language_code="en",
        left_group_key="group-0001",
        right_group_key="group-0002",
        left_claim=make_claim(
            "The officer said there was no vehicle contact."
        ),
        right_claim=make_claim(
            "Garces-Perez said the ICE SUV caused the collision."
        ),
        candidate_score=0.72,
    )


def make_success_payload():
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": (
                            '{"decisions":[{'
                            '"left_group_key":"group-0001",'
                            '"right_group_key":"group-0002",'
                            '"relation_kind":"disputes",'
                            '"confidence":0.94,'
                            '"reason":"Competing accounts."'
                            "}]}"),
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": 812,
            "output_tokens": 47,
        },
    }


def test_luna_provider_uses_responses_structured_output(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {
                "output": [
                    {
                        "type": "reasoning",
                        "summary": [],
                    },
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": (
                                    '{"decisions":[{'
                                    '"left_group_key":"group-0001",'
                                    '"right_group_key":"group-0002",'
                                    '"relation_kind":"disputes",'
                                    '"confidence":0.94,'
                                    '"reason":"Competing accounts of the same collision."'
                                    "}]}"),
                            }
                        ],
                    },
                ],
                "usage": {
                    "input_tokens": 812,
                    "output_tokens": 47,
                },
            }
        )

    monkeypatch.setattr(
        "app.claim_relations.openai_provider.httpx.post",
        fake_post,
    )

    provider = OpenAISemanticClaimRelationProvider(
        api_key="test-key",
    )
    decisions = provider.classify((make_candidate(),))

    assert captured["url"] == (
        "https://api.openai.com/v1/responses"
    )
    request = captured["json"]
    assert request["model"] == "gpt-6-luna"
    assert request["store"] is False
    assert request["reasoning"] == {"effort": "low"}
    assert (
        request["text"]["format"]["type"]
        == "json_schema"
    )
    assert request["text"]["format"]["strict"] is True

    assert len(decisions) == 1
    assert (
        decisions[0].relation_kind
        == SemanticRelationKind.DISPUTES
    )
    assert decisions[0].confidence == 0.94
    assert "Competing accounts" in decisions[0].reason
    assert provider.last_usage is not None
    assert provider.last_usage.input_tokens == 812
    assert provider.last_usage.output_tokens == 47


def test_luna_provider_rejects_refusal(monkeypatch):
    def fake_post(_url, **_kwargs):
        return FakeResponse(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "refusal",
                                "refusal": "cannot classify",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "app.claim_relations.openai_provider.httpx.post",
        fake_post,
    )

    provider = OpenAISemanticClaimRelationProvider(
        api_key="test-key",
    )
    with pytest.raises(
        ValueError,
        match="refused",
    ):
        provider.classify((make_candidate(),))


def test_luna_provider_does_not_call_api_for_empty_candidates(
    monkeypatch,
):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("HTTP should not be called")

    monkeypatch.setattr(
        "app.claim_relations.openai_provider.httpx.post",
        unexpected_post,
    )
    provider = OpenAISemanticClaimRelationProvider(
        api_key="test-key",
    )

    assert provider.classify(()) == ()
    assert provider.last_usage is not None
    assert provider.last_usage.input_tokens == 0
    assert provider.last_usage.output_tokens == 0


def test_luna_provider_configuration_never_contains_api_key():
    provider = OpenAISemanticClaimRelationProvider(
        api_key="super-secret",
    )

    configuration = provider.configuration()

    assert configuration["model"] == "gpt-6-luna"
    assert configuration["base_url"] == (
        "https://api.openai.com/v1"
    )
    assert configuration["prompt_version"] == "3"
    assert "super-secret" not in str(configuration)


def test_luna_prompt_requires_actual_incompatibility_for_disputes():
    prompt = OpenAISemanticClaimRelationProvider._system_prompt()

    assert "actual point of incompatibility" in prompt
    assert "addition of compatible facts are NOT disputes" in prompt
    assert "NEVER choose disputes" in prompt
    assert "wrong leg was amputated" in prompt
    assert "X and Y cannot both be" in prompt


def test_luna_provider_retries_temporary_rate_limit(monkeypatch):
    responses = [
        FakeResponse(
            {
                "error": {
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                }
            },
            status_code=429,
            headers={"Retry-After": "0"},
        ),
        FakeResponse(make_success_payload()),
    ]
    calls = []
    sleeps = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(
        "app.claim_relations.openai_provider.httpx.post",
        fake_post,
    )
    monkeypatch.setattr(
        "app.claim_relations.openai_provider.time.sleep",
        sleeps.append,
    )

    provider = OpenAISemanticClaimRelationProvider(
        api_key="test-key",
        rate_limit_max_retries=1,
        rate_limit_fallback_seconds=1,
    )
    decisions = provider.classify((make_candidate(),))

    assert len(decisions) == 1
    assert len(calls) == 2
    assert sleeps == [0.5]


def test_luna_provider_does_not_retry_spend_limit(monkeypatch):
    calls = []
    sleeps = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            {
                "error": {
                    "type": "rate_limit_error",
                    "code": "project_spend_limit_exceeded",
                }
            },
            status_code=429,
            headers={"Retry-After": "60"},
        )

    monkeypatch.setattr(
        "app.claim_relations.openai_provider.httpx.post",
        fake_post,
    )
    monkeypatch.setattr(
        "app.claim_relations.openai_provider.time.sleep",
        sleeps.append,
    )

    provider = OpenAISemanticClaimRelationProvider(
        api_key="test-key",
        rate_limit_max_retries=3,
    )
    with pytest.raises(httpx.HTTPStatusError):
        provider.classify((make_candidate(),))

    assert len(calls) == 1
    assert sleeps == []


def test_luna_provider_paces_consecutive_requests(monkeypatch):
    monotonic_values = iter([0.0, 0.0, 10.0, 31.0])
    sleeps = []

    monkeypatch.setattr(
        "app.claim_relations.openai_provider.time.monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(
        "app.claim_relations.openai_provider.time.sleep",
        sleeps.append,
    )
    monkeypatch.setattr(
        "app.claim_relations.openai_provider.httpx.post",
        lambda *_args, **_kwargs: FakeResponse(
            make_success_payload()
        ),
    )

    provider = OpenAISemanticClaimRelationProvider(
        api_key="test-key",
        min_request_interval_seconds=31,
    )
    provider.classify((make_candidate(),))
    provider.classify((make_candidate(),))

    assert sleeps == [21.0]
