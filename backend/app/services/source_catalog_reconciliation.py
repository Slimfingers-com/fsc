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
            source_action = entry.get("source_action", "create_source")
            source = self._get_runtime_source(
                db,
                source_name,
            )

            if source is None:
                if source_action == "extend_existing_source":
                    conflicts.append(
                        f"{source_name}: existing_source_key "
                        f"{entry['existing_source_key']!r} does not resolve "
                        "to an existing runtime Source"
                    )
                    continue

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
                                f"{len(entry.get('feeds') or [])} reviewed "
                                "feed(s)"
                            ),
                        )
                    )
                continue

            self._refresh_runtime_relationships(db, source)

            source_conflicts = self._source_identity_conflicts(
                source=source,
                entry=entry,
                catalog=catalog,
            )
            conflicts.extend(source_conflicts)
            if source_conflicts:
                continue

            outlet_actions, outlet_conflicts = self._plan_outlets(
                source=source,
                catalog=catalog,
                entry=entry,
            )
            actions.extend(outlet_actions)
            conflicts.extend(outlet_conflicts)
            if outlet_conflicts:
                continue

            feed_actions, feed_conflicts = self._plan_feeds(
                db,
                source=source,
                entry=entry,
            )
            actions.extend(feed_actions)
            conflicts.extend(feed_conflicts)

            if not outlet_actions and not feed_actions:
                actions.append(
                    CatalogReconciliationAction(
                        action="no_change",
                        source_name=source_name,
                        detail="runtime Source already matches catalog entry",
                    )
                )

        return CatalogReconciliationReport(
            catalog_name=catalog_name,
            actions=tuple(actions),
            conflicts=tuple(conflicts),
        )

    @staticmethod
    def _refresh_runtime_relationships(
        db: Session,
        source: Any,
    ) -> None:
        db.flush()
        db.expire(source, ["feeds", "outlets"])

    def _plan_feeds(
        self,
        db: Session,
        *,
        source: Any,
        entry: dict[str, Any],
    ) -> tuple[list[CatalogReconciliationAction], list[str]]:
        actions: list[CatalogReconciliationAction] = []
        conflicts: list[str] = []
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

        for feed_data in entry.get("feeds") or []:
            url = feed_data["url"]
            name = feed_data["name"].strip()
            existing_by_url = by_url.get(url)

            if existing_by_url is not None:
                if self._feed_needs_update(
                    existing_by_url,
                    feed_data,
                ):
                    actions.append(
                        CatalogReconciliationAction(
                            action="update_feed",
                            source_name=source.name,
                            feed_name=name,
                            detail=url,
                        )
                    )
                else:
                    actions.append(
                        CatalogReconciliationAction(
                            action="no_change",
                            source_name=source.name,
                            feed_name=name,
                            detail=url,
                        )
                    )
                continue

            existing_global = self.source_service.repository.get_feed_by_url(
                db,
                url,
            )
            if (
                existing_global is not None
                and existing_global.source_id != source.id
            ):
                conflicts.append(
                    f"{source.name}: feed URL {url} belongs to another Source"
                )
                continue

            existing_by_name = by_name.get(name.casefold())
            if existing_by_name is not None:
                conflicts.append(
                    f"{source.name}: feed name {name!r} already exists "
                    f"with URL {existing_by_name.url}"
                )
                continue

            actions.append(
                CatalogReconciliationAction(
                    action="create_feed",
                    source_name=source.name,
                    feed_name=name,
                    detail=url,
                )
            )

        return actions, conflicts

    def _plan_outlets(
        self,
        *,
        source: Any,
        catalog: dict[str, Any],
        entry: dict[str, Any],
    ) -> tuple[list[CatalogReconciliationAction], list[str]]:
        actions: list[CatalogReconciliationAction] = []
        conflicts: list[str] = []
        outlet_data = self._entry_outlet_data(catalog, entry)
        if not outlet_data:
            return actions, conflicts

        active_outlets = [
            outlet
            for outlet in source.outlets
            if outlet.deleted_at is None
        ]
        by_name = {
            outlet.normalized_name: outlet
            for outlet in active_outlets
        }
        source_action = entry.get("source_action", "create_source")
        has_primary = any(outlet.is_primary for outlet in active_outlets)

        for index, data in enumerate(outlet_data):
            expected = self._outlet_create(
                catalog,
                entry,
                data,
                index=index,
                source_action=source_action,
            )
            normalized = normalize_source_name(expected.name)
            existing = by_name.get(normalized)
            if existing is None:
                if expected.is_primary and has_primary:
                    conflicts.append(
                        f"{source.name}: reviewed primary outlet "
                        f"{expected.name!r} is missing while another "
                        "active primary outlet already exists"
                    )
                    continue
                actions.append(
                    CatalogReconciliationAction(
                        action="create_outlet",
                        source_name=source.name,
                        detail=expected.name,
                    )
                )
                if expected.is_primary:
                    has_primary = True
                continue

            conflict = self._outlet_conflict(existing, expected)
            if conflict is not None:
                conflicts.append(
                    f"{source.name}: {conflict}"
                )

        return actions, conflicts

    def _apply(
        self,
        db: Session,
        *,
        catalog: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> None:
        for entry in entries:
            source_name = entry["name"].strip()
            source_action = entry.get("source_action", "create_source")
            source = self._get_runtime_source(
                db,
                source_name,
            )

            if source is None:
                if source_action == "extend_existing_source":
                    raise BusinessRuleViolationError(
                        f"{source_name}: existing runtime Source is missing"
                    )
                self.source_service.create_source(
                    db,
                    self._source_create(catalog, entry),
                )
                continue

            self._refresh_runtime_relationships(db, source)

            self._apply_outlets(
                db,
                source=source,
                catalog=catalog,
                entry=entry,
            )

            active_feeds = [
                feed
                for feed in source.feeds
                if feed.deleted_at is None
            ]
            by_url = {
                feed.url: feed
                for feed in active_feeds
            }

            for feed_data in entry.get("feeds") or []:
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

    def _apply_outlets(
        self,
        db: Session,
        *,
        source: Any,
        catalog: dict[str, Any],
        entry: dict[str, Any],
    ) -> None:
        outlet_data = self._entry_outlet_data(catalog, entry)
        if not outlet_data:
            return

        active_outlets = [
            outlet
            for outlet in source.outlets
            if outlet.deleted_at is None
        ]
        by_name = {
            outlet.normalized_name: outlet
            for outlet in active_outlets
        }
        source_action = entry.get("source_action", "create_source")
        has_primary = any(outlet.is_primary for outlet in active_outlets)

        for index, data in enumerate(outlet_data):
            expected = self._outlet_create(
                catalog,
                entry,
                data,
                index=index,
                source_action=source_action,
            )
            normalized = normalize_source_name(expected.name)
            if normalized in by_name:
                continue
            self.source_service.create_outlet(
                db,
                source,
                expected,
            )
            created = True

        if created:
            self._refresh_runtime_relationships(db, source)

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

        source_type = (
            catalog.get("organization_type")
            or catalog.get("runtime_source_type")
        )
        country = catalog.get("country")
        role_policy = catalog.get("feed_role_policy") or {}
        if not source_type or not country or not role_policy:
            raise BusinessRuleViolationError(
                "Catalog activation metadata is incomplete."
            )

        materializable: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for entry in self._catalog_entries(catalog):
            feeds = entry.get("feeds") or []
            source_action = entry.get("source_action", "create_source")
            outlet_data = self._entry_outlet_data(catalog, entry)

            if source_action == "create_source":
                if not feeds:
                    continue
            elif source_action == "extend_existing_source":
                if not entry.get("existing_source_key"):
                    raise BusinessRuleViolationError(
                        f"{entry.get('name')}: extend_existing_source "
                        "requires existing_source_key."
                    )
                if not feeds and not outlet_data:
                    continue
            else:
                if feeds:
                    raise BusinessRuleViolationError(
                        f"{entry.get('name')}: unsupported source_action "
                        f"{source_action!r}."
                    )
                continue

            entry_source_type = entry.get("source_type") or source_type
            if entry_source_type != source_type:
                raise BusinessRuleViolationError(
                    f"{entry.get('name')}: SourceType differs from catalog."
                )
            entry_country = entry.get("country") or country
            if entry_country != country:
                raise BusinessRuleViolationError(
                    f"{entry.get('name')}: country differs from catalog."
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

    def _get_runtime_source(
        self,
        db: Session,
        source_name: str,
    ) -> Any | None:
        source = self.source_service.repository.get_by_normalized_name(
            db,
            normalize_source_name(source_name),
        )
        if source is None:
            return None
        return (
            self.source_service.get_by_slug(db, source.slug)
            or source
        )

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
        expected_type = SourceType(
            entry.get("source_type")
            or catalog.get("organization_type")
            or catalog["runtime_source_type"]
        )
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
    def _outlet_create(
        catalog: dict[str, Any],
        entry: dict[str, Any],
        data: dict[str, Any],
        *,
        index: int,
        source_action: str,
    ) -> SourceOutletCreate:
        explicit_primary = data.get("is_primary")
        if explicit_primary is None:
            is_primary = (
                source_action == "create_source"
                and index == 0
            )
        else:
            is_primary = explicit_primary

        return SourceOutletCreate(
            name=data["name"],
            media_category=(
                data.get("media_category")
                or catalog.get("media_category")
            ),
            publication_form=(
                data.get("publication_form")
                or entry.get("publication_form")
                or "other"
            ),
            language=(
                data.get("language")
                or entry.get("language")
                or catalog.get("language")
            ),
            url=data.get("homepage") or data.get("url"),
            is_primary=is_primary,
            active=data.get("active", True),
        )

    @staticmethod
    def _outlet_conflict(
        existing: Any,
        expected: SourceOutletCreate,
    ) -> str | None:
        actual = (
            str(existing.media_category),
            str(existing.publication_form),
            existing.language,
            existing.url,
            existing.is_primary,
            existing.active,
        )
        wanted = (
            str(expected.media_category),
            str(expected.publication_form),
            expected.language,
            str(expected.url) if expected.url else None,
            expected.is_primary,
            expected.active,
        )
        if actual == wanted:
            return None
        return (
            f"existing outlet {expected.name!r} differs from reviewed "
            "media/form/language/url/primary/active metadata"
        )

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

    @staticmethod
    def _catalog_entries(
        catalog: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            *[
                entry
                for group in catalog.get("groups", [])
                for entry in group.get("entries", [])
            ],
            *catalog.get("unclassified_entries", []),
        ]

    @staticmethod
    def _entry_outlet_data(
        catalog: dict[str, Any],
        entry: dict[str, Any],
    ) -> list[dict[str, Any]]:
        outlets = list(entry.get("outlets") or [])
        if outlets:
            return outlets

        publication_form = entry.get("publication_form")
        media_category = catalog.get("media_category")
        if publication_form and media_category:
            return [
                {
                    "name": entry["name"],
                    "media_category": media_category,
                    "publication_form": publication_form,
                    "language": (
                        entry.get("language")
                        or catalog.get("language")
                    ),
                    "homepage": entry.get("homepage"),
                }
            ]
        return []

    def _source_create(
        self,
        catalog: dict[str, Any],
        entry: dict[str, Any],
    ) -> SourceCreate:
        catalog_language = catalog.get("language")
        outlet_data = self._entry_outlet_data(catalog, entry)
        outlets = [
            self._outlet_create(
                catalog,
                entry,
                outlet,
                index=index,
                source_action="create_source",
            )
            for index, outlet in enumerate(outlet_data)
        ]
        source_type = (
            entry.get("source_type")
            or catalog.get("organization_type")
            or catalog["runtime_source_type"]
        )
        return SourceCreate(
            name=entry["name"],
            url=entry["homepage"],
            source_type=source_type,
            coverage_scope=catalog.get("runtime_coverage_scope"),
            country=entry.get("country") or catalog.get("country"),
            language=entry.get("language") or catalog_language,
            feeds=[
                self._feed_create(feed)
                for feed in entry["feeds"]
            ],
            outlets=outlets,
        )
