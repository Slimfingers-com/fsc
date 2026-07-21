from __future__ import annotations

import hashlib
import html
import math
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0

_WHITESPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)


@dataclass(frozen=True, slots=True)
class NormalizedContent:
    title: str | None
    text: str | None
    language_code: str | None
    word_count: int
    reading_time_minutes: int
    content_hash: str


class ContentNormalizer:
    VERSION = 1
    WORDS_PER_MINUTE = 200

    def normalize(
        self,
        *,
        title: str | None,
        summary: str | None,
        content: str | None,
    ) -> NormalizedContent:
        normalized_title = self._normalize_fragment(title)
        source_body = content if self._has_text(content) else summary
        normalized_text = self._normalize_fragment(source_body)
        word_count = len(_WORD_RE.findall(normalized_text or ""))
        reading_time = (
            max(1, math.ceil(word_count / self.WORDS_PER_MINUTE))
            if word_count
            else 0
        )
        language_code = self._detect_language(
            " ".join(part for part in (normalized_title, normalized_text) if part)
        )
        digest_source = "\n".join(
            part for part in (normalized_title or "", normalized_text or "")
        )
        content_hash = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
        return NormalizedContent(
            title=normalized_title,
            text=normalized_text,
            language_code=language_code,
            word_count=word_count,
            reading_time_minutes=reading_time,
            content_hash=content_hash,
        )

    @staticmethod
    def _has_text(value: str | None) -> bool:
        return bool(value and value.strip())

    @staticmethod
    def _normalize_fragment(value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        soup = BeautifulSoup(value, "html.parser")
        for element in soup(["script", "style", "noscript", "template"]):
            element.decompose()
        text = soup.get_text(" ")
        text = html.unescape(text)
        text = _WHITESPACE_RE.sub(" ", text).strip()
        return text or None

    @staticmethod
    def _detect_language(value: str) -> str | None:
        if len(value) < 20:
            return None
        try:
            return detect(value)
        except LangDetectException:
            return None
