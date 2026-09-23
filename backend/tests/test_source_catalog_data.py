import json
from pathlib import Path

import pytest


CATALOG_DIR = Path(__file__).parents[1] / "catalog"
CATALOG_FILES = {
    "DE": CATALOG_DIR / "de_print_v1.json",
    "AT": CATALOG_DIR / "at_print_v1.json",
    "CH": CATALOG_DIR / "ch_print_v1.json",
    "GB": CATALOG_DIR / "gb_print_v1.json",
    "US": CATALOG_DIR / "us_print_v1.json",
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
ALLOWED_METRIC_KINDS = {
    "sold_circulation",
    "distributed_circulation",
    "print_run",
    "print_readers",
    "digital_unique_users",
    "visits",
    "page_impressions",
    "paid_digital_subscriptions",
    "subscribers",
}


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
    assert catalog["coverage_policy"] == "targets_are_goals_not_quotas"
    assert catalog["coverage_policy_notes"]

    keys: set[str] = set()
    names: set[str] = set()

    assert all(group["key"] not in {"boulevard", "general_unclassified"} for group in catalog["groups"])
    assert catalog["groups"]

    for group in catalog["groups"]:
        assert isinstance(group["entries"], list)
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

        if newspapers < newspaper_min or magazines < magazine_min:
            assert catalog["coverage_policy"] == "targets_are_goals_not_quotas"
            assert group.get("coverage_exception")


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
        "GB": {
            "Süddeutsche Zeitung",
            "Frankfurter Allgemeine Zeitung",
            "Der Standard",
            "Die Presse",
            "Neue Zürcher Zeitung",
            "Die Weltwoche",
            "Schweizer Monat",
            "Schweizerzeit",
        },
        "US": {
            "Süddeutsche Zeitung",
            "Frankfurter Allgemeine Zeitung",
            "Der Standard",
            "Die Presse",
            "Neue Zürcher Zeitung",
            "Die Weltwoche",
            "Schweizer Monat",
            "Schweizerzeit",
            "The Guardian",
            "The Telegraph",
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
    } | {
        entry["language"]
        for entry in catalog.get("unclassified_entries", [])
    }
    assert entry_languages == {"de", "fr", "it", "rm"}


def test_inactive_20_minuten_print_is_not_in_switzerland_catalog() -> None:
    catalog = load_catalog("CH")
    names = {
        entry["name"]
        for group in catalog["groups"]
        for entry in group["entries"]
    } | {
        entry["name"]
        for entry in catalog.get("unclassified_entries", [])
    }
    assert names.isdisjoint({"20 Minuten", "20 minutes", "20 minuti"})


def test_non_political_print_attributes_are_not_political_groups() -> None:
    for country in CATALOG_FILES:
        catalog = load_catalog(country)
        group_keys = {group["key"] for group in catalog["groups"]}
        assert "boulevard" not in group_keys
        assert "general_unclassified" not in group_keys
        for entry in catalog.get("unclassified_entries", []):
            assert set(entry.get("format_tags", [])) & {"boulevard", "politically_unclassified"}


def test_party_press_is_a_separate_dimension() -> None:
    expected = {
        "AT": {"Neue Freie Zeitung": "FPÖ"},
        "CH": {"SVP-Klartext": "SVP", "Schweizer Demokrat": "Schweizer Demokraten"},
    }
    for country, titles in expected.items():
        catalog = load_catalog(country)
        entries = {
            entry["name"]: entry
            for group in catalog["groups"]
            for entry in group["entries"]
        }
        for name, affiliation in titles.items():
            assert entries[name]["party_press"] is True
            assert entries[name]["party_affiliation"] == affiliation

    for country in CATALOG_FILES:
        catalog = load_catalog(country)
        assert "party_press" not in {group["key"] for group in catalog["groups"]}


def test_gb_catalog_covers_constituent_countries_and_welsh() -> None:
    catalog = load_catalog("GB")
    assert set(catalog["regional_scope"]) == {"England", "Scotland", "Wales", "Northern Ireland"}
    entries = [entry for group in catalog["groups"] for entry in group["entries"]] + catalog.get("unclassified_entries", [])
    assert {entry["subnational_region"] for entry in entries} == {"England", "Scotland", "Wales", "Northern Ireland"}
    assert {"en", "cy"} <= {entry["language"] for entry in entries}


def test_gb_constitutional_position_is_not_forced_onto_left_right_axis() -> None:
    catalog = load_catalog("GB")
    unclassified = {entry["name"]: entry for entry in catalog.get("unclassified_entries", [])}
    assert "The Irish News" in unclassified
    assert "News Letter" in unclassified
    for name in ("The Irish News", "News Letter"):
        assert "politically_unclassified" in unclassified[name]["format_tags"]


def test_gb_sunday_editions_use_brand_outlet_policy() -> None:
    catalog = load_catalog("GB")
    assert catalog["edition_policy"] == "brand_as_source_print_products_as_outlets"


def test_us_catalog_keeps_sparse_groups_as_documented_exceptions() -> None:
    catalog = load_catalog("US")
    groups = {group["key"]: group for group in catalog["groups"]}
    for key in ("radical_left", "liberal_centre", "conservative", "right", "radical_right"):
        assert groups[key].get("coverage_exception")


def test_us_spanish_print_can_remain_politically_unclassified() -> None:
    catalog = load_catalog("US")
    unclassified = {entry["name"]: entry for entry in catalog.get("unclassified_entries", [])}
    assert "La Opinión" in unclassified
    assert unclassified["La Opinión"]["language"] == "es"
    assert "politically_unclassified" in unclassified["La Opinión"]["format_tags"]


def test_us_catalog_excludes_discontinued_american_renaissance_print() -> None:
    catalog = load_catalog("US")
    names = {entry["name"] for group in catalog["groups"] for entry in group["entries"]}
    assert "American Renaissance" not in names


def test_die_tagespost_is_not_marked_as_party_press() -> None:
    catalog = load_catalog("DE")
    entries = {entry["name"]: entry for group in catalog["groups"] for entry in group["entries"]}
    assert entries["Die Tagespost"].get("party_press") is not True
    assert entries["Die Tagespost"].get("party_affiliation") is None


EUROPE_CATALOG = CATALOG_DIR / "europe_print_v1.json"


def test_europe_catalog_is_regional_and_country_metadata_is_per_entry() -> None:
    catalog = json.loads(EUROPE_CATALOG.read_text(encoding="utf-8"))
    assert catalog["scope"] == "europe"
    assert catalog["country"] is None
    assert set(catalog["countries_excluded"]) == {"DE", "AT", "CH", "GB"}
    entries = [entry for group in catalog["groups"] for entry in group["entries"]]
    assert len(entries) == 50
    assert len({entry["key"] for entry in entries}) == 50
    assert all(entry["country"] not in catalog["countries_excluded"] for entry in entries)
    assert all(entry["country"] for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)
    assert all(entry["catalog_status"] == "candidate" for entry in entries)
    assert all(entry["publication_form"] in ALLOWED_FORMS for entry in entries)
    assert all(entry["form_group"] in ALLOWED_FORM_GROUPS for entry in entries)
    assert all(entry["language"] in set(catalog["languages"]) for entry in entries)


def test_europe_catalog_keeps_political_provenance_attributed() -> None:
    catalog = json.loads(EUROPE_CATALOG.read_text(encoding="utf-8"))
    for group in catalog["groups"]:
        for entry in group["entries"]:
            for classification in entry["classifications"]:
                assert classification["classifier_name"]
                assert classification["classifier_type"]
                assert classification["source_url"].startswith("https://")
                assert classification["reference_date"]
                assert classification["retrieved_at"]
                assert "not an FSC assessment" in classification.get("notes", "")


def test_europe_catalog_does_not_reintroduce_detailed_country_blocks() -> None:
    catalog = json.loads(EUROPE_CATALOG.read_text(encoding="utf-8"))
    assert catalog["scope"] == "europe"
    assert "coverage_targets" not in catalog
    assert catalog["target_catalog_size"]["guideline_target"] == 50
    assert catalog["target_catalog_size"]["hard_cap"] is False


INTERNATIONAL_CATALOG = CATALOG_DIR / "international_print_v1.json"


def test_international_catalog_is_regional_and_excludes_us_and_europe() -> None:
    catalog = json.loads(INTERNATIONAL_CATALOG.read_text(encoding="utf-8"))
    assert catalog["scope"] == "international"
    assert catalog["country"] is None
    assert catalog["countries_excluded"] == ["US"]
    assert catalog["regions_excluded"] == ["Europe"]
    assert catalog["target_catalog_size"]["hard_cap"] is False

    entries = [entry for group in catalog["groups"] for entry in group["entries"]] + catalog["unclassified_entries"]
    assert len(entries) == 40
    assert len({entry["key"] for entry in entries}) == 40
    assert len({entry["name"].casefold() for entry in entries}) == 40
    assert all(entry["country"] != "US" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)
    assert all(entry["catalog_status"] == "candidate" for entry in entries)
    assert all(entry["activity_status"] in ALLOWED_ACTIVITY for entry in entries)
    assert all(entry["publication_form"] in ALLOWED_FORMS for entry in entries)
    assert all(entry["form_group"] in ALLOWED_FORM_GROUPS for entry in entries)
    assert all(entry["language"] in set(catalog["languages"]) for entry in entries)


def test_international_catalog_preserves_unmapped_political_positions() -> None:
    catalog = json.loads(INTERNATIONAL_CATALOG.read_text(encoding="utf-8"))
    assert catalog["political_mapping_review"]["status"] == "resolved_preserve_unmapped"
    assert catalog["review_status"]["political_mapping"] == "decision_2_two_source_threshold"
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"
    assert all(
        len(entry["classifications"]) >= 2
        for group in catalog["groups"]
        for entry in group["entries"]
    )
    assert all(
        "politically_unclassified" in entry["format_tags"]
        for entry in catalog["unclassified_entries"]
    )


def test_international_catalog_metadata_provenance_is_complete() -> None:
    catalog = json.loads(INTERNATIONAL_CATALOG.read_text(encoding="utf-8"))
    entries = [entry for group in catalog["groups"] for entry in group["entries"]] + catalog["unclassified_entries"]
    for entry in entries:
        for classification in entry["classifications"]:
            assert classification["dimension"]
            assert classification["value"]
            assert classification["classifier_type"]
            assert classification["classifier_name"]
            assert classification["source_url"].startswith("https://")
            assert classification["reference_date"]
            assert classification["retrieved_at"]
        for metric in entry["metrics"]:
            assert metric["metric_kind"] in ALLOWED_METRIC_KINDS
            assert metric["value"] >= 0
            assert metric["unit"]
            assert metric["reference_period"]
            assert metric["measurement_body"]
            assert metric["source_url"].startswith("https://")
            assert metric["retrieved_at"]
