from collections import defaultdict
from datetime import date, datetime
from uuid import UUID

from app.enums.source_dependency import SourceRelationKind
from app.models.source_dependency import ArticleProvenance, SourceRelation


class SourceIndependenceResolver:
    COLLAPSING_RELATION_KINDS = {
        SourceRelationKind.EDITORIAL_PARENT,
        SourceRelationKind.SHARED_NEWSROOM,
        SourceRelationKind.JOINT_EDITORIAL_OPERATION,
    }

    def __init__(
        self,
        *,
        relations: tuple[SourceRelation, ...],
        provenance: tuple[ArticleProvenance, ...],
    ) -> None:
        self.relations = relations
        self.provenance = provenance
        self._provenance_by_article: dict[
            UUID,
            tuple[ArticleProvenance, ...],
        ] = {}
        grouped: dict[UUID, list[ArticleProvenance]] = defaultdict(list)
        for item in provenance:
            grouped[item.article_id].append(item)
        self._provenance_by_article = {
            article_id: tuple(
                sorted(
                    items,
                    key=lambda value: (
                        str(value.upstream_source_id),
                        str(value.id),
                    ),
                )
            )
            for article_id, items in grouped.items()
        }
        self._source_key_cache: dict[
            tuple[UUID, date | None],
            str,
        ] = {}

    @staticmethod
    def _as_date(value: datetime | date | None) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        return value

    @staticmethod
    def _relation_applies(
        relation: SourceRelation,
        on_date: date | None,
    ) -> bool:
        if on_date is None:
            return (
                relation.valid_from is None
                and relation.valid_to is None
            )
        if (
            relation.valid_from is not None
            and on_date < relation.valid_from
        ):
            return False
        if (
            relation.valid_to is not None
            and on_date > relation.valid_to
        ):
            return False
        return True

    def source_key(
        self,
        source_id: UUID,
        *,
        at: datetime | date | None = None,
    ) -> str:
        on_date = self._as_date(at)
        cache_key = (source_id, on_date)
        cached = self._source_key_cache.get(cache_key)
        if cached is not None:
            return cached

        component = {source_id}
        frontier = {source_id}

        while frontier:
            next_frontier: set[UUID] = set()
            for relation in self.relations:
                if (
                    relation.relation_kind
                    not in self.COLLAPSING_RELATION_KINDS
                ):
                    continue
                if not self._relation_applies(
                    relation,
                    on_date,
                ):
                    continue
                if relation.source_id in frontier:
                    other = relation.related_source_id
                elif relation.related_source_id in frontier:
                    other = relation.source_id
                else:
                    continue
                if other not in component:
                    component.add(other)
                    next_frontier.add(other)
            frontier = next_frontier

        canonical = min(component, key=str)
        result = f"source:{canonical}"
        for member in component:
            self._source_key_cache[(member, on_date)] = result
        return result

    def article_key(
        self,
        *,
        article_id: UUID,
        source_id: UUID,
        at: datetime | date | None = None,
    ) -> str:
        upstream = self._provenance_by_article.get(
            article_id,
            (),
        )
        if upstream:
            return min(
                self.source_key(
                    item.upstream_source_id,
                    at=at,
                )
                for item in upstream
            )
        return self.source_key(
            source_id,
            at=at,
        )
