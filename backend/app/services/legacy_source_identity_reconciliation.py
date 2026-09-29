from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationError
from app.core.source_identity import normalize_source_name
from app.enums.coverage_scope import CoverageScope
from app.enums.source_metadata import PublicationForm, SourceMedium
from app.enums.source_type import SourceType
from app.schemas.source_metadata import SourceOutletCreate
from app.services.source import SourceService


@dataclass(frozen=True)
class CanonicalOutletSpec:
    name: str
    media_category: SourceMedium
    publication_form: PublicationForm
    url: str
    language: str = "de"
    is_primary: bool = False


@dataclass(frozen=True)
class LegacySourceIdentitySpec:
    legacy_slug: str
    accepted_names: tuple[str, ...]
    canonical_name: str
    canonical_url: str
    source_type: SourceType
    coverage_scope: CoverageScope
    country: str
    language: str
    outlets: tuple[CanonicalOutletSpec, ...]


@dataclass(frozen=True)
class LegacyIdentityAction:
    action: str
    slug: str
    detail: str


@dataclass(frozen=True)
class LegacyIdentityReport:
    actions: tuple[LegacyIdentityAction, ...]
    conflicts: tuple[str, ...]

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def change_count(self) -> int:
        return sum(action.action != "no_change" for action in self.actions)


LEGACY_SOURCE_IDENTITY_SPECS = (
    LegacySourceIdentitySpec(
        legacy_slug="deutschlandfunk",
        accepted_names=("Deutschlandfunk", "Deutschlandradio"),
        canonical_name="Deutschlandradio",
        canonical_url="https://www.deutschlandradio.de/",
        source_type=SourceType.NEWS,
        coverage_scope=CoverageScope.NATIONAL,
        country="DE",
        language="de",
        outlets=(
            CanonicalOutletSpec(
                name="Deutschlandfunk",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.RADIO,
                url="https://www.deutschlandfunk.de/",
                is_primary=True,
            ),
            CanonicalOutletSpec(
                name="Deutschlandfunk Kultur",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.RADIO,
                url="https://www.deutschlandfunkkultur.de/",
            ),
            CanonicalOutletSpec(
                name="Deutschlandfunk Nova",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.RADIO,
                url="https://www.deutschlandfunknova.de/",
            ),
        ),
    ),
    LegacySourceIdentitySpec(
        legacy_slug="tagesschau-de",
        accepted_names=("tagesschau.de", "ARD-aktuell"),
        canonical_name="ARD-aktuell",
        canonical_url="https://www.tagesschau.de/",
        source_type=SourceType.NEWS,
        coverage_scope=CoverageScope.NATIONAL,
        country="DE",
        language="de",
        outlets=(
            CanonicalOutletSpec(
                name="tagesschau.de",
                media_category=SourceMedium.DIGITAL,
                publication_form=PublicationForm.OTHER,
                url="https://www.tagesschau.de/",
                is_primary=True,
            ),
            CanonicalOutletSpec(
                name="Tagesschau",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.TELEVISION,
                url="https://www.tagesschau.de/",
            ),
            CanonicalOutletSpec(
                name="Tagesthemen",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.TELEVISION,
                url=(
                    "https://www.tagesschau.de/multimedia/"
                    "sendung/tagesthemen/"
                ),
            ),
            CanonicalOutletSpec(
                name="tagesschau24",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.TELEVISION,
                url="https://www.tagesschau.de/multimedia/livestreams/",
            ),
        ),
    ),
    LegacySourceIdentitySpec(
        legacy_slug="zdfheute",
        accepted_names=("ZDFheute", "ZDF"),
        canonical_name="ZDF",
        canonical_url="https://www.zdf.de/nachrichten/",
        source_type=SourceType.NEWS,
        coverage_scope=CoverageScope.NATIONAL,
        country="DE",
        language="de",
        outlets=(
            CanonicalOutletSpec(
                name="ZDFheute",
                media_category=SourceMedium.DIGITAL,
                publication_form=PublicationForm.OTHER,
                url="https://www.zdf.de/nachrichten/",
                is_primary=True,
            ),
            CanonicalOutletSpec(
                name="ZDF Nachrichten",
                media_category=SourceMedium.BROADCAST,
                publication_form=PublicationForm.TELEVISION,
                url="https://www.zdf.de/nachrichten/",
            ),
        ),
    ),
)


class LegacySourceIdentityReconciler:
    """Canonicalize known legacy Source identities without changing their IDs."""

    def __init__(
        self,
        source_service: SourceService | None = None,
        specs: Iterable[LegacySourceIdentitySpec] | None = None,
    ) -> None:
        self.source_service = source_service or SourceService()
        self.specs = tuple(specs or LEGACY_SOURCE_IDENTITY_SPECS)

    def reconcile(
        self,
        db: Session,
        *,
        apply: bool = False,
    ) -> LegacyIdentityReport:
        report = self._plan(db)

        if report.has_conflicts:
            if apply:
                raise BusinessRuleViolationError(
                    "Legacy Source identity conflicts: "
                    + "; ".join(report.conflicts)
                )
            return report

        if apply:
            self._apply(db)

        return report

    def _plan(self, db: Session) -> LegacyIdentityReport:
        actions: list[LegacyIdentityAction] = []
        conflicts: list[str] = []

        for spec in self.specs:
            source = self.source_service.get_by_slug(db, spec.legacy_slug)
            if source is None:
                conflicts.append(
                    f"{spec.legacy_slug}: expected legacy Source is missing"
                )
                continue

            source_conflicts = self._source_conflicts(
                db,
                source=source,
                spec=spec,
            )
            conflicts.extend(source_conflicts)
            if source_conflicts:
                continue

            if source.name != spec.canonical_name:
                actions.append(
                    LegacyIdentityAction(
                        action="canonicalize_source_name",
                        slug=spec.legacy_slug,
                        detail=(
                            f"{source.name!r} -> {spec.canonical_name!r}; "
                            "slug and UUID remain unchanged"
                        ),
                    )
                )

            if source.url != spec.canonical_url:
                actions.append(
                    LegacyIdentityAction(
                        action="update_source_url",
                        slug=spec.legacy_slug,
                        detail=f"{source.url} -> {spec.canonical_url}",
                    )
                )

            outlets_by_name = {
                outlet.normalized_name: outlet
                for outlet in source.outlets
                if outlet.deleted_at is None
            }
            for outlet_spec in spec.outlets:
                normalized = normalize_source_name(outlet_spec.name)
                existing = outlets_by_name.get(normalized)
                if existing is None:
                    actions.append(
                        LegacyIdentityAction(
                            action="create_outlet",
                            slug=spec.legacy_slug,
                            detail=outlet_spec.name,
                        )
                    )
                    continue

                outlet_conflict = self._outlet_conflict(
                    existing,
                    outlet_spec,
                )
                if outlet_conflict is not None:
                    conflicts.append(
                        f"{spec.legacy_slug}: {outlet_conflict}"
                    )

            if (
                source.name == spec.canonical_name
                and source.url == spec.canonical_url
                and all(
                    normalize_source_name(outlet.name) in outlets_by_name
                    for outlet in spec.outlets
                )
                and not any(
                    conflict.startswith(f"{spec.legacy_slug}:")
                    for conflict in conflicts
                )
            ):
                actions.append(
                    LegacyIdentityAction(
                        action="no_change",
                        slug=spec.legacy_slug,
                        detail="canonical identity already applied",
                    )
                )

        return LegacyIdentityReport(
            actions=tuple(actions),
            conflicts=tuple(conflicts),
        )

    def _apply(self, db: Session) -> None:
        for spec in self.specs:
            source = self.source_service.get_by_slug(db, spec.legacy_slug)
            if source is None:
                raise BusinessRuleViolationError(
                    f"{spec.legacy_slug}: expected legacy Source is missing"
                )

            source.name = spec.canonical_name
            source.normalized_name = normalize_source_name(
                spec.canonical_name
            )
            source.url = spec.canonical_url

            outlets_by_name = {
                outlet.normalized_name: outlet
                for outlet in source.outlets
                if outlet.deleted_at is None
            }
            for outlet_spec in spec.outlets:
                normalized = normalize_source_name(outlet_spec.name)
                if normalized in outlets_by_name:
                    continue
                self.source_service.create_outlet(
                    db,
                    source,
                    SourceOutletCreate(
                        name=outlet_spec.name,
                        media_category=outlet_spec.media_category,
                        publication_form=outlet_spec.publication_form,
                        language=outlet_spec.language,
                        url=outlet_spec.url,
                        is_primary=outlet_spec.is_primary,
                        active=True,
                    ),
                )

        self.source_service.repository.flush(db)

    def _source_conflicts(
        self,
        db: Session,
        *,
        source,
        spec: LegacySourceIdentitySpec,
    ) -> list[str]:
        conflicts: list[str] = []

        if source.name not in spec.accepted_names:
            conflicts.append(
                f"{spec.legacy_slug}: unexpected Source name {source.name!r}"
            )

        canonical_normalized = normalize_source_name(spec.canonical_name)
        canonical_source = (
            self.source_service.repository.get_by_normalized_name(
                db,
                canonical_normalized,
            )
        )
        if (
            canonical_source is not None
            and canonical_source.id != source.id
        ):
            conflicts.append(
                f"{spec.legacy_slug}: canonical name "
                f"{spec.canonical_name!r} belongs to another Source"
            )

        if source.source_type != spec.source_type:
            conflicts.append(
                f"{spec.legacy_slug}: SourceType "
                f"{source.source_type.value} differs from "
                f"{spec.source_type.value}"
            )
        if source.coverage_scope != spec.coverage_scope:
            current = (
                source.coverage_scope.value
                if source.coverage_scope is not None
                else None
            )
            conflicts.append(
                f"{spec.legacy_slug}: coverage_scope {current!r} differs "
                f"from {spec.coverage_scope.value!r}"
            )
        if source.country != spec.country:
            conflicts.append(
                f"{spec.legacy_slug}: country {source.country!r} differs "
                f"from {spec.country!r}"
            )
        if source.language != spec.language:
            conflicts.append(
                f"{spec.legacy_slug}: language {source.language!r} differs "
                f"from {spec.language!r}"
            )

        return conflicts

    @staticmethod
    def _outlet_conflict(existing, spec: CanonicalOutletSpec) -> str | None:
        actual = (
            existing.media_category,
            existing.publication_form,
            existing.language,
            existing.url,
            existing.is_primary,
            existing.active,
        )
        expected = (
            spec.media_category,
            spec.publication_form,
            spec.language,
            spec.url,
            spec.is_primary,
            True,
        )
        if actual == expected:
            return None
        return (
            f"existing outlet {spec.name!r} differs from canonical "
            "media/form/language/url/primary/active metadata"
        )
