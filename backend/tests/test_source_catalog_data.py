import json
from pathlib import Path


CATALOG_PATH = Path(__file__).parents[1] / "catalog" / "de_print_v1.json"

ALLOWED_FORMS = {
    "daily_newspaper",
    "weekly_newspaper",
    "sunday_newspaper",
    "magazine",
    "periodical",
}
ALLOWED_ACTIVITY = {"active", "verify_current"}
ALLOWED_FORM_GROUPS = {"newspaper_or_weekly", "magazine_or_periodical"}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_de_print_catalog_is_catalog_only_and_unique() -> None:
    catalog = load_catalog()

    assert catalog["country"] == "DE"
    assert catalog["language"] == "de"
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

            # A reviewed catalog must never activate ingestion by itself.
            assert entry["feeds"] == []


def test_de_print_catalog_meets_group_targets_or_documents_exception() -> None:
    catalog = load_catalog()
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

        assert magazines >= magazine_min
        if newspapers < newspaper_min:
            assert group.get("coverage_exception")
        else:
            assert newspapers >= newspaper_min


def test_country_block_contains_no_at_or_ch_titles() -> None:
    catalog = load_catalog()
    excluded = {"Schweizer Monat", "Schweizerzeit", "NZZ", "Weltwoche"}
    actual = {
        entry["name"]
        for group in catalog["groups"]
        for entry in group["entries"]
    }

    assert actual.isdisjoint(excluded)
