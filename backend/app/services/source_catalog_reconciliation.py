from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationError
from app.core.source_identity import normalize_source_name
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate, FeedUpdate
from app.schemas.source import SourceCreate
from app.schemas.source_metadata import SourceOutletCreate
from app.services.source import SourceService


REVIEWED_FEED_ACTIVATION_POLICY = (
    "only_verified_relevant_official_content_channels_are_activated"
)
CATALOG_ONLY_FEED_CLASS_POLICY = (
    "catalog_review_metadata_only_not_persisted"
)


@dataclass(frozen=True)
class CatalogReconciliationAction:
    action: str
    source_name: str
    feed_name: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class CatalogReconciliationReport:
    catalog_name: str
    actions: tuple[CatalogReconciliationAction, ...]
    conflicts: tuple[str, ...]

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def change_count(self) -> int:
        return sum(
            action.action != "no_change"
            for action in self.actions
        )


class SourceCatalogReconciler:
    """Materialize only reviewed catalog entries that contain configured feeds."""

    def __init__(
        self,
        source_service: SourceService | None = None,
    ) -> None:
        self.source_service = source_service or SourceService()

    def reconcile(
        self,
        db: Session,
        catalog: dict[str, Any],
        *,
        catalog_name: str,
        apply: bool = False,
    ) -> CatalogReconciliationReport:
        entries = self._validated_materializable_entries(catalog)
        report = self._plan(
            db,
            catalog=catalog,
            entries=entries,
            catalog_name=catalog_name,
        )

        if report.has_conflicts:
            if apply:
                raise BusinessRuleViolationError(
                    "Catalog reconciliation conflicts: "
                    + "; ".join(report.conflicts)
                )
            return report

        if apply:
            self._apply(
                db,
                catalog=catalog,
                entries=entries,
            )

        return report

    def _plan(
        self,
        db: Session,
        *,
        catalog: dict[str, Any],
        entries: list[dict[str, Any]],
        catalog_name: str,
    ) -> CatalogReconciliationReport:
        actions: list[CatalogReconciliationAction] = []
        conflicts: list[str] = []

        for entry in entries:
            source_name = entry["name"].strip()
            normalized_name = normalize_source_name(source_name)
            source = self.source_service.repository.get_by_normalized_name(
                db,
                normalized_name,
            )

            if source is None:
                entry_conflicts = self._new_source_conflicts(
                    db,
                    entry,
                )
                conflicts.extend(entry_conflicts)
                if not entry_conflicts:
                    actions.append(
                        CatalogReconciliationAction(
                            action="create_source",
                            source_name=source_name,
                            detail=(
                                f"{len(entry['feeds'])} reviewed feed(s)"
                            ),
                        )
                    )
                continue

            source_conflicts = self._source_identity_conflicts(
                source=source,
                entry=entry,
                catalog=catalog,
            )
            conflicts.extend(source_conflicts)
            if source_conflicts:
                continue

            active_feeds = [
                feed
                for feed in source.feeds
                if feed.deleted_at is None
            ]
            by_url = {
                feed.url: feed
                for feed in active_feeds
            }
            by_name = {
                feed.name.strip().casefold(): feed
                for feed in active_feeds
            }

            for feed_data in entry["feeds"]:
                url = feed_data["url"]
                name = feed_data["name"].strip()
                existing_by_url = by_url.get(url)

                if existing_by_url is not None:
                    if existing_by_url.source_id != source.id:
                        conflicts.append(
                            f"{source_name}: feed URL {url} belongs to "
                            "another Source"
                        )
                        continue

                    if self._feed_needs_update(
                        existing_by_url,
                        feed_data,
                    ):
                        actions.append(
                            CatalogReconciliationAction(
                                action="update_feed",
                                source_name=source_name,
                                feed_name=name,
                                detail=url,
                            )
                        )
                    else:
                        actions.append(
                            CatalogReconciliationAction(
                                action="no_change",
                                source_name=source_name,
                                feed_name=name,
                                detail=url,
                            )
                        )
                    continue

                existing_global = (
                    self.source_service.repository.get_feed_by_url(
                        db,
                        url,
                    )
                )
                if (
                    existing_global is not None
                    and existing_global.source_id != source.id
                ):
                    conflicts.append(
                        f"{source_name}: feed URL {url} belongs to "
                        "another Source"
                    )
                    continue

                existing_by_name = by_name.get(name.casefold())
                if existing_by_name is not None:
                    conflicts.append(
                        f"{source_name}: feed name {name!r} already exists "
                        f"with URL {existing_by_name.url}"
                    )
                    continue

                actions.append(
                    CatalogReconciliationAction(
                        action="create_feed",
                        source_name=source_name,
                        feed_name=name,
                        detail=url,
                    )
                )

        return CatalogReconciliationReport(
            catalog_name=catalog_name,
            actions=tuple(actions),
            conflicts=tuple(conflicts),
        )

    def _apply(
        self,
        db: Session,
        *,
        catalog: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> None:
        for entry in entries:
            source_name = entry["name"].strip()
            source = self.source_service.repository.get_by_normalized_name(
                db,
                normalize_source_name(source_name),
            )

            if source is None:
                self.source_service.create_source(
                    db,
                    self._source_create(entry),
                )
                continue

            active_feeds = [
                feed
                for feed in source.feeds
                if feed.deleted_at is None
            ]
            by_url = {
                feed.url: feed
                for feed in active_feeds
            }

            for feed_data in entry["feeds"]:
                existing = by_url.get(feed_data["url"])
                if existing is None:
                    self.source_service.create_feed(
                        db,
                        source,
                        self._feed_create(feed_data),
                    )
                    continue

                if self._feed_needs_update(existing, feed_data):
                    self.source_service.update_feed(
                        db,
                        source,
                        existing.id,
                        FeedUpdate(
                            name=feed_data["name"],
                            active=feed_data["active"],
                            priority=feed_data["priority"],
                            fetch_interval_minutes=(
                                feed_data["fetch_interval_minutes"]
                            ),
                            default_confirmation_role=(
                                feed_data["default_confirmation_role"]
                            ),
                        ),
                    )

    def _validated_materializable_entries(
        self,
        catalog: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if (
            catalog.get("feed_activation_policy")
            != REVIEWED_FEED_ACTIVATION_POLICY
        ):
            raise BusinessRuleViolationError(
                "Catalog is not marked as reviewed for feed activation."
            )
        if (
            catalog.get("feed_class_policy")
            != CATALOG_ONLY_FEED_CLASS_POLICY
        ):
            raise BusinessRuleViolationError(
                "Catalog feed_class policy is not supported."
            )

        catalog_source_type = (
            catalog.get("organization_type")
            or catalog.get("source_type")
        )
        country = catalog.get("country")
        language = catalog.get("language")
        role_policy = catalog.get("feed_role_policy") or {}
        if not country or not role_policy:
            raise BusinessRuleViolationError(
                "Catalog activation metadata is incomplete."
            )

        materializable: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        entries = [
            entry
            for group in catalog.get("groups", [])
            for entry in group.get("entries", [])
        ]
        entries.extend(catalog.get("unclassified_entries", []))

        for raw_entry in entries:
            feeds = raw_entry.get("feeds") or []
            if not feeds:
                continue

            entry = dict(raw_entry)
            resolved_source_type = (
                entry.get("source_type")
                or catalog_source_type
            )
            if not resolved_source_type:
                raise BusinessRuleViolationError(
                    f"{entry.get('name')}: SourceType is missing."
                )
            entry["source_type"] = resolved_source_type
            entry["country"] = entry.get("country") or country
            entry["language"] = entry.get("language") or language
            entry["source_action"] = (
                entry.get("source_action")
                or "create_source"
            )

            if (
                catalog_source_type
                and resolved_source_type != catalog_source_type
            ):
                raise BusinessRuleViolationError(
                    f"{entry.get('name')}: SourceType differs from catalog."
                )
            if entry.get("country") != country:
                raise BusinessRuleViolationError(
                    f"{entry.get('name')}: country differs from catalog."
                )
            if entry.get("source_action") != "create_source":
                raise BusinessRuleViolationError(
                    f"{entry.get('name')}: unsupported source_action."
                )

            for feed in feeds:
                feed_class = feed.get("feed_class")
                expected_role = role_policy.get(feed_class)
                if expected_role is None:
                    raise BusinessRuleViolationError(
                        f"{entry.get('name')}: unsupported feed_class "
                        f"{feed_class!r}."
                    )
                if feed.get("default_confirmation_role") != expected_role:
                    raise BusinessRuleViolationError(
                        f"{entry.get('name')}: feed role does not match "
                        "the reviewed feed-class policy."
                    )
                tier = feed.get("activation_tier")
                if tier not in {1, 2}:
                    raise BusinessRuleViolationError(
                        f"{entry.get('name')}: invalid activation tier."
                    )
                if feed.get("active") is not (tier == 1):
                    raise BusinessRuleViolationError(
                        f"{entry.get('name')}: active flag does not match "
                        "activation tier."
                    )
                url = feed.get("url")
                if not url or url in seen_urls:
                    raise BusinessRuleViolationError(
                        "Configured feed URLs must be present and unique "
                        "within a catalog."
                    )
                seen_urls.add(url)

            materializable.append(entry)

        return materializable

    def _new_source_conflicts(
        self,
        db: Session,
        entry: dict[str, Any],
    ) -> list[str]:
        conflicts: list[str] = []
        for feed_data in entry["feeds"]:
            existing = self.source_service.repository.get_feed_by_url(
                db,
                feed_data["url"],
            )
            if existing is not None:
                conflicts.append(
                    f"{entry['name']}: feed URL {feed_data['url']} "
                    "already belongs to a runtime Source"
                )
        return conflicts

    @staticmethod
    def _source_identity_conflicts(
        *,
        source: Any,
        entry: dict[str, Any],
        catalog: dict[str, Any],
    ) -> list[str]:
        conflicts: list[str] = []
        expected_type = SourceType(entry["source_type"])
        if source.source_type != expected_type:
            conflicts.append(
                f"{entry['name']}: runtime SourceType "
                f"{source.source_type.value} differs from "
                f"{expected_type.value}"
            )
        expected_country = catalog["country"]
        if source.country not in {None, expected_country}:
            conflicts.append(
                f"{entry['name']}: runtime country {source.country} differs "
                f"from {expected_country}"
            )
        return conflicts

    @staticmethod
    def _feed_needs_update(
        feed: Any,
        data: dict[str, Any],
    ) -> bool:
        role = (
            feed.default_confirmation_role.value
            if feed.default_confirmation_role is not None
            else None
        )
        return any(
            (
                feed.name != data["name"],
                feed.active != data["active"],
                feed.priority != data["priority"],
                feed.fetch_interval_minutes
                != data["fetch_interval_minutes"],
                role != data["default_confirmation_role"],
            )
        )

    @staticmethod
    def _feed_create(
        data: dict[str, Any],
    ) -> FeedCreate:
        return FeedCreate(
            name=data["name"],
            url=data["url"],
            active=data["active"],
            priority=data["priority"],
            fetch_interval_minutes=data["fetch_interval_minutes"],
            default_confirmation_role=data["default_confirmation_role"],
        )

    def _source_create(
        self,
        entry: dict[str, Any],
    ) -> SourceCreate:
        outlets = [
            SourceOutletCreate(
                name=outlet["name"],
                media_category=outlet["media_category"],
                publication_form=outlet["publication_form"],
                language=outlet.get("language"),
                url=outlet.get("homepage"),
                is_primary=index == 0,
                active=True,
            )
            for index, outlet in enumerate(entry.get("outlets") or [])
        ]
        return SourceCreate(
            name=entry["name"],
            url=entry["homepage"],
            source_type=entry["source_type"],
            country=entry.get("country"),
            language=entry.get("language"),
            feeds=[
                self._feed_create(feed)
                for feed in entry["feeds"]
            ],
            outlets=outlets,
        )
