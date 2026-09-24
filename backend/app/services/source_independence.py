from collections import defaultdict
from datetime import date, datetime
from uuid import UUID

from app.enums.source_dependency import (
    ArticleProvenanceKind,
    SourceRelationKind,
)
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
        grouped: dict[UUID, list[ArticleProvenance]] = defaultdict(list)
        for item in provenance:
            grouped[item.article_id].append(item)
        self._provenance_by_article: dict[
            UUID,
            tuple[ArticleProvenance, ...],
        ] = {
            article_id: tuple(
                sorted(
                    items,
                    key=lambda value: (
                        str(value.upstream_source_id),
                        str(value.upstream_article_id or ""),
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
        self._article_dependency_cache: dict[
            tuple[UUID, UUID, date | None],
            frozenset[str],
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

    def article_dependency_keys(
        self,
        *,
        article_id: UUID,
        source_id: UUID,
        at: datetime | date | None = None,
        _trail: frozenset[UUID] = frozenset(),
    ) -> frozenset[str]:
        on_date = self._as_date(at)
        cache_key = (article_id, source_id, on_date)
        cached = self._article_dependency_cache.get(cache_key)
        if cached is not None:
            return cached

        if article_id in _trail:
            return frozenset(
                {self.source_key(source_id, at=at)}
            )

        upstream = self._provenance_by_article.get(
            article_id,
            (),
        )
        if not upstream:
            result = frozenset(
                {self.source_key(source_id, at=at)}
            )
            self._article_dependency_cache[cache_key] = result
            return result

        dependencies: set[str] = set()
        if any(
            item.relation_kind
            == ArticleProvenanceKind.CO_PRODUCED_WITH
            for item in upstream
        ):
            dependencies.add(
                self.source_key(source_id, at=at)
            )

        next_trail = _trail | {article_id}
        for item in upstream:
            if item.upstream_article_id is not None:
                dependencies.update(
                    self.article_dependency_keys(
                        article_id=item.upstream_article_id,
                        source_id=item.upstream_source_id,
                        at=at,
                        _trail=next_trail,
                    )
                )
            else:
                dependencies.add(
                    self.source_key(
                        item.upstream_source_id,
                        at=at,
                    )
                )

        if not dependencies:
            dependencies.add(
                self.source_key(source_id, at=at)
            )

        result = frozenset(dependencies)
        self._article_dependency_cache[cache_key] = result
        return result

    def article_component_keys(
        self,
        *,
        articles: tuple[
            tuple[
                UUID,
                UUID,
                datetime | date | None,
            ],
            ...,
        ],
    ) -> dict[UUID, str]:
        dependencies_by_article: dict[
            UUID,
            frozenset[str],
        ] = {}
        for article_id, source_id, at in articles:
            dependencies_by_article[article_id] = (
                self.article_dependency_keys(
                    article_id=article_id,
                    source_id=source_id,
                    at=at,
                )
            )

        parent: dict[str, str] = {}

        def find(value: str) -> str:
            root = parent.setdefault(value, value)
            while root != parent[root]:
                root = parent[root]
            current = value
            while current != root:
                next_value = parent[current]
                parent[current] = root
                current = next_value
            return root

        def union(left: str, right: str) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root == right_root:
                return
            canonical = min(left_root, right_root)
            other = (
                right_root
                if canonical == left_root
                else left_root
            )
            parent[other] = canonical

        for dependencies in dependencies_by_article.values():
            ordered = sorted(dependencies)
            if not ordered:
                continue
            for dependency in ordered:
                parent.setdefault(dependency, dependency)
            first = ordered[0]
            for dependency in ordered[1:]:
                union(first, dependency)

        return {
            article_id: find(min(dependencies))
            for article_id, dependencies
            in dependencies_by_article.items()
            if dependencies
        }

    def article_key(
        self,
        *,
        article_id: UUID,
        source_id: UUID,
        at: datetime | date | None = None,
    ) -> str:
        return self.article_component_keys(
            articles=((article_id, source_id, at),)
        )[article_id]
