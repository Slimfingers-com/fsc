from inspect import signature

from app.search.provider import SearchFilters, SearchPage, SearchProvider, SearchSort


class StubProvider(SearchProvider):
    def search(self, *, query, filters, sort, page, page_size):
        return SearchPage(items=[], total=0, page=page, page_size=page_size)


def test_provider_abstraction_has_no_sqlalchemy_session():
    parameters = signature(SearchProvider.search).parameters
    assert "db" not in parameters
    assert "session" not in parameters
    result = StubProvider().search(
        query="topic", filters=SearchFilters(), sort=SearchSort.RELEVANCE,
        page=1, page_size=20,
    )
    assert result.total == 0
