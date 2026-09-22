from __future__ import annotations

import math
from abc import ABC, abstractmethod

import httpx


EmbeddingVector = tuple[float, ...]


def cosine_similarity(
    left: EmbeddingVector,
    right: EmbeddingVector,
) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    value = dot / (left_norm * right_norm)
    return max(-1.0, min(1.0, value))


class EmbeddingProvider(ABC):
    provider: str
    version: str
    model: str

    @abstractmethod
    def embed(
        self,
        texts: tuple[str, ...],
    ) -> tuple[EmbeddingVector, ...]: ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    provider = "openai"
    version = "1"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        timeout_seconds: float = 30.0,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key must not be empty")
        if not model:
            raise ValueError("embedding model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")

    def embed(
        self,
        texts: tuple[str, ...],
    ) -> tuple[EmbeddingVector, ...]:
        if not texts:
            return ()

        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": list(texts),
                "encoding_format": "float",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()

        raw_items = payload.get("data")
        if not isinstance(raw_items, list):
            raise ValueError("embedding response does not contain a data list")

        by_index: dict[int, EmbeddingVector] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                raise ValueError("embedding response item must be an object")
            index = item.get("index")
            vector = item.get("embedding")
            if not isinstance(index, int) or not isinstance(vector, list):
                raise ValueError("embedding response item is malformed")

            typed: list[float] = []
            for value in vector:
                if not isinstance(value, (int, float)):
                    raise ValueError("embedding values must be numeric")
                numeric = float(value)
                if not math.isfinite(numeric):
                    raise ValueError("embedding values must be finite")
                typed.append(numeric)

            if not typed:
                raise ValueError("embedding vector must not be empty")
            by_index[index] = tuple(typed)

        expected = set(range(len(texts)))
        if set(by_index) != expected:
            raise ValueError("embedding response indexes do not match inputs")

        dimension = len(by_index[0])
        if any(len(vector) != dimension for vector in by_index.values()):
            raise ValueError("embedding dimensions are inconsistent")

        return tuple(by_index[index] for index in range(len(texts)))
