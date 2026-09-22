import json
from pathlib import Path

import pytest


CATALOG_DIR = Path(__file__).parents[1] / "catalog"
CATALOG_FILES = {
    "DE": CATALOG_DIR / "de_print_v1.json",
    "AT": CATALOG_DIR / "at_print_v1.json",
    "CH": CATALOG_DIR / "ch_print_v1.json",
}

ALLOWED_FORMS = {
    "daily_newspaper",
    "weekly_newspaper",
    "sunday_newspaper",
    "magazine",
    "periodical",
}
ALLOWED_ACTIVITY = {"active", "verify_current"}
ALLOWED_FORM_GROUPS = {"newspaper_or_weekly", "magazine_or_periodical"}


def load_catalog(country: str) -> dict:
    return json.loads(CATALOG_FILES[country].read_text(encoding="utf-8"))


def catalog_languages(catalog: dict) -> set[str]:
    if "languages" in catalog:
        return set(catalog["languages"])
    return {catalog["language"]}


@pytest.mark.parametrize("country", CATALOG_FILES)
def test_print_catalog_is_catalog_only_and_unique(country: str) -> None:
    catalog = load_catalog(country)

    assert catalog["country"] == country
    assert catalog_languages(catalog)
    assert catalog["media_category"] == "print"
    assert catalog["activation_policy"] == "catalog_only_until_joint_review"

    keys: set[str] = set()
    names: set[str] = set()

    for group in catalog["groups"]:
        assert group["entries"]
        for entry in group["entries"]:
            assert entry["key"] not in keys
            assert entry["name"].casefold() not in names
            keys.add(entry["key"])
            names.add(entry["name"].casefold())

            assert entry["publication_form"] in ALLOWED_FORMS
            assert entry["form_group"] in ALLOWED_FORM_GROUPS
            assert entry["activity_status"] in ALLOWED_ACTIVITY
            assert entry["catalog_status"] == "candidate"
            assert entry["feeds"] == []

            if "language" in entry:
                assert entry["language"] in catalog_languages(catalog)


@pytest.mark.parametrize("country", CATALOG_FILES)
def test_print_catalog_meets_targets_or_documents_exception(country: str) -> None:
    catalog = load_catalog(country)
    newspaper_min = catalog["coverage_targets"]["newspaper_or_weekly_min"]
    magazine_min = catalog["coverage_targets"]["magazine_or_periodical_min"]

    for group in catalog["groups"]:
        newspapers = sum(
            entry["form_group"] == "newspaper_or_weekly"
            for entry in group["entries"]
        )
        magazines = sum(
            entry["form_group"] == "magazine_or_periodical"
            for entry in group["entries"]
        )

        if group.get("group_kind") in {"format", "unclassified"}:
            if len(group["entries"]) < 3:
                assert group.get("coverage_exception")
            continue

        if newspapers < newspaper_min:
            assert group.get("coverage_exception")
        else:
            assert newspapers >= newspaper_min

        if magazines < magazine_min:
            assert group.get("coverage_exception")
        else:
            assert magazines >= magazine_min


def test_country_blocks_do_not_mix_de_at_ch_titles() -> None:
    excluded = {
        "DE": {
            "Der Standard",
            "Die Presse",
            "Neue Zürcher Zeitung",
            "Die Weltwoche",
            "Schweizer Monat",
            "Schweizerzeit",
        },
        "AT": {
            "Süddeutsche Zeitung",
            "Frankfurter Allgemeine Zeitung",
            "Neue Zürcher Zeitung",
            "Die Weltwoche",
            "Schweizer Monat",
            "Schweizerzeit",
        },
        "CH": {
            "Süddeutsche Zeitung",
            "Frankfurter Allgemeine Zeitung",
            "Der Standard",
            "Die Presse",
        },
    }

    for country in CATALOG_FILES:
        catalog = load_catalog(country)
        actual = {
            entry["name"]
            for group in catalog["groups"]
            for entry in group["entries"]
        }
        assert actual.isdisjoint(excluded[country])


@pytest.mark.parametrize("country", CATALOG_FILES)
def test_catalog_metadata_records_are_provenance_complete(country: str) -> None:
    catalog = load_catalog(country)

    for group in catalog["groups"]:
        for entry in group["entries"]:
            for classification in entry["classifications"]:
                assert classification["dimension"]
                assert classification["value"]
                assert classification["classifier_type"]
                assert classification["classifier_name"]
                assert classification["source_url"].startswith("https://")
                assert classification["reference_date"]
                assert classification["retrieved_at"]

            for metric in entry["metrics"]:
                assert metric["metric_kind"]
                assert metric["value"] >= 0
                assert metric["unit"]
                assert metric["reference_period"]
                assert metric["measurement_body"]
                assert metric["source_url"].startswith("https://")
                assert metric["retrieved_at"]


def test_switzerland_catalog_covers_all_national_languages() -> None:
    catalog = load_catalog("CH")
    assert set(catalog["languages"]) == {"de", "fr", "it", "rm"}

    entry_languages = {
        entry["language"]
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    assert entry_languages == {"de", "fr", "it", "rm"}


def test_inactive_20_minuten_print_is_not_in_switzerland_catalog() -> None:
    catalog = load_catalog("CH")
    names = {
        entry["name"]
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    assert names.isdisjoint({"20 Minuten", "20 minutes", "20 minuti"})
