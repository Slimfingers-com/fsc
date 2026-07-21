from app.content.normalizer import ContentNormalizer


def test_normalizer_removes_markup_and_unsafe_elements():
    result = ContentNormalizer().normalize(
        title=" <b> Hello&nbsp;World </b> ",
        summary=None,
        content="<p>First <strong>paragraph</strong>.</p><script>bad()</script><p>Second.</p>",
    )
    assert result.title == "Hello World"
    assert result.text == "First paragraph . Second."
    assert "bad" not in result.text
    assert result.word_count == 3
    assert result.reading_time_minutes == 1
    assert len(result.content_hash) == 64


def test_normalizer_falls_back_to_summary():
    result = ContentNormalizer().normalize(
        title=None,
        summary="<p>This is the fallback summary with enough words for detection.</p>",
        content="   ",
    )
    assert result.text == "This is the fallback summary with enough words for detection."
    assert result.language_code == "en"


def test_normalizer_is_deterministic():
    normalizer = ContentNormalizer()
    first = normalizer.normalize(title="Title", summary="Body text", content=None)
    second = normalizer.normalize(title="Title", summary="Body text", content=None)
    assert first.content_hash == second.content_hash
