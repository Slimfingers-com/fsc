from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.models.article import Article
from app.models.search_document import SearchDocument
from app.repositories.search_document import SearchDocumentRepository
from app.search.builder import SearchDocumentBuilder


@dataclass(frozen=True, slots=True)
class SearchIndexBatchResult:
    processed: int
    created: int
    updated: int


class SearchIndexingService:
    def __init__(self, repository: SearchDocumentRepository | None = None, builder: SearchDocumentBuilder | None = None) -> None:
        self.repository = repository or SearchDocumentRepository()
        self.builder = builder or SearchDocumentBuilder()

    def index_article(self, db: Session, article: Article) -> bool:
        data = self.builder.build(article)
        document = self.repository.get_by_article_id(db, data.article_id)
        values = asdict(data)
        if document is None:
            self.repository.add(db, SearchDocument(**values))
            return True
        for key, value in values.items():
            setattr(document, key, value)
        return False


class SearchIndexingRunner:
    def __init__(self, session_factory: sessionmaker[Session], service: SearchIndexingService | None = None) -> None:
        self.session_factory = session_factory
        self.service = service or SearchIndexingService()

    def run_pending(self, *, limit: int) -> SearchIndexBatchResult:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        with self.session_factory() as db:
            with db.begin():
                articles = self.service.repository.list_pending_articles(
                    db, builder_version=self.service.builder.VERSION, limit=limit
                )
                created = sum(self.service.index_article(db, article) for article in articles)
            return SearchIndexBatchResult(processed=len(articles), created=created, updated=len(articles) - created)
