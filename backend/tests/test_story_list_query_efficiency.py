"""Query-shape regressions for bounded Story listing.

Full API integration tests verify the result sets; this test protects the
query plan shape at realistic production cardinalities (100k+ articles).
"""
import pytest
from sqlalchemy.dialects import postgresql

from app.stories.postgresql import PostgreSQLStoryReadProvider
from app.stories.provider import StoryFilters, StorySort


class RecordingSession:
    def __init__(self):
        self.count_sql = ""
        self.page_sql = ""

    def scalar(self, statement):
        self.count_sql = str(statement.compile(dialect=postgresql.dialect()))
        return 0

    def execute(self, statement):
        self.page_sql = str(statement.compile(dialect=postgresql.dialect()))
        return self

    def all(self):
        return []


@pytest.mark.parametrize("sort", list(StorySort))
@pytest.mark.parametrize("language", (None, "de", "en"))
def test_story_list_limits_representative_title_join_to_current_page(sort, language):
    db = RecordingSession()
    result = PostgreSQLStoryReadProvider(db).list_stories(
        filters=StoryFilters(language_code=language, min_sources=2),
        sort=sort,
        page=3,
        page_size=20,
    )

    assert result.total == 0
    assert result.page == 3
    assert result.items == []
    # The count should never perform the full-corpus representative-title
    # DISTINCT ON, which is unnecessary for exact source/article counts.
    assert "story_representative_title" not in db.count_sql
    assert "story_page_summaries" not in db.count_sql

    # Only the requested page needs representative titles.
    assert "story_page_summaries" in db.page_sql
    assert "story_representative_title" in db.page_sql
    assert "IN (SELECT story_page_summaries.story_id" in db.page_sql
