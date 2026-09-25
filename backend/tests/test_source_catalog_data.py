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
    "radio_daily_listeners",
    "radio_hourly_listeners",
    "radio_market_share",
    "tv_viewers",
    "tv_daily_reach",
    "tv_market_share",
}
ALLOWED_CLASSIFIER_TYPES = {
    "self_description",
    "media_database",
    "academic",
    "public_authority",
    "court",
    "publisher",
    "other",
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
    assert len(entries) == len(catalog["curated_shortlist"])
    assert catalog["target_catalog_size"]["guideline_range"][0] <= len(entries) <= catalog["target_catalog_size"]["guideline_range"][1]
    assert len({entry["key"] for entry in entries}) == len(entries)
    assert len({entry["name"].casefold() for entry in entries}) == len(entries)
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
        len({
            item["classifier_name"]
            for item in entry["classifications"]
            if item["dimension"] == "editorial_orientation"
        }) >= 2
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
            assert classification["classifier_type"] in ALLOWED_CLASSIFIER_TYPES
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
            assert metric["metric_scope"]
            assert isinstance(metric["audited"], bool)
            assert metric["source_url"].startswith("https://")
            assert metric["retrieved_at"]


def test_international_catalog_models_state_control_separately() -> None:
    catalog = json.loads(INTERNATIONAL_CATALOG.read_text(encoding="utf-8"))
    assert catalog["scope_review"]["status"] == "resolved_include_with_control_metadata"
    entries = {
        entry["name"]: entry
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    entries.update({entry["name"]: entry for entry in catalog["unclassified_entries"]})
    expected = {
        "People's Daily": "party_official",
        "Global Times": "party_state_affiliated",
        "China Daily": "party_state_managed",
        "The Straits Times": "state_managed_public_service_media",
    }
    for name, value in expected.items():
        entry = entries[name]
        assert "politically_unclassified" in entry["format_tags"]
        assert any(
            item["dimension"] == "media_positioning" and item["value"] == value
            for item in entry["classifications"]
        )


def test_international_sparse_political_groups_are_not_filled_by_quota() -> None:
    catalog = json.loads(INTERNATIONAL_CATALOG.read_text(encoding="utf-8"))
    groups = {group["key"]: group for group in catalog["groups"]}
    for key in ("radical_left", "liberal_centre", "radical_right"):
        assert groups[key].get("coverage_exception")
    for group in catalog["groups"]:
        for entry in group["entries"]:
            orientation_sources = {
                item["classifier_name"]
                for item in entry["classifications"]
                if item["dimension"] == "editorial_orientation"
            }
            assert len(orientation_sources) >= 2


def test_international_core_is_germany_focused_and_deferred_is_explicit() -> None:
    catalog = json.loads(INTERNATIONAL_CATALOG.read_text(encoding="utf-8"))
    entries = [entry for group in catalog["groups"] for entry in group["entries"]] + catalog["unclassified_entries"]
    names = {entry["name"] for entry in entries}
    shortlist_names = {item["name"] for item in catalog["curated_shortlist"]}

    assert names == shortlist_names
    assert all(entry["activity_status"] == "active" for entry in entries)
    assert catalog["deferred_candidates"]
    assert names.isdisjoint({item["name"] for item in catalog["deferred_candidates"]})
    assert all(item["reason"] for item in catalog["deferred_candidates"])
    assert {entry["country"] for entry in entries}.isdisjoint({"TW", "HK"})
    assert catalog["review_status"]["scope"] == "decision_c_no_taiwan_hong_kong_currently"


def test_print_products_are_not_duplicate_sources() -> None:
    gb = load_catalog("GB")
    gb_entries = [entry for group in gb["groups"] for entry in group["entries"]] + gb.get("unclassified_entries", [])
    gb_by_name = {entry["name"]: entry for entry in gb_entries}
    assert "The Guardian Weekly" not in gb_by_name
    assert {outlet["name"] for outlet in gb_by_name["The Guardian"]["outlets"]} == {
        "The Guardian",
        "The Guardian Weekly",
    }

    ch = load_catalog("CH")
    ch_entries = [entry for group in ch["groups"] for entry in group["entries"]] + ch.get("unclassified_entries", [])
    ch_by_name = {entry["name"]: entry for entry in ch_entries}
    assert "SonntagsBlick" not in ch_by_name
    assert {outlet["name"] for outlet in ch_by_name["Blick"]["outlets"]} == {
        "Blick",
        "SonntagsBlick",
    }
    assert {metric.get("outlet_name") for metric in ch_by_name["Blick"]["metrics"]} == {
        "Blick",
        "SonntagsBlick",
    }


DE_BROADCAST_CATALOG = CATALOG_DIR / "de_broadcast_v1.json"


def load_de_broadcast_catalog() -> dict:
    return json.loads(DE_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def test_de_national_broadcast_catalog_has_approved_editorial_sources() -> None:
    catalog = load_de_broadcast_catalog()
    assert catalog["country"] == "DE"
    assert catalog["scope"] == "national"
    assert catalog["media_category"] == "broadcast"
    assert catalog["activation_policy"] == "catalog_only_until_joint_review"
    assert catalog["source_identity_policy"] == "one_editorial_source_multiple_programmes_and_channels_as_outlets"
    assert catalog["approved_candidate_count"] == 15
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"

    entries = [entry for group in catalog["groups"] for entry in group["entries"]]
    assert len(entries) == 15
    assert len({entry["key"] for entry in entries}) == 15
    assert len({entry["name"].casefold() for entry in entries}) == 15
    assert all(entry["catalog_status"] == "candidate" for entry in entries)
    assert all(entry["activity_status"] == "active" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)
    assert all(entry["outlets"] for entry in entries)
    assert all(
        outlet["publication_form"] in {"radio", "television"}
        for entry in entries
        for outlet in entry["outlets"]
    )


def test_de_national_broadcast_deduplicates_programmes_into_editorial_sources() -> None:
    catalog = load_de_broadcast_catalog()
    entries = {
        entry["name"]: entry
        for group in catalog["groups"]
        for entry in group["entries"]
    }

    assert {outlet["name"] for outlet in entries["Deutschlandradio"]["outlets"]} == {
        "Deutschlandfunk",
        "Deutschlandfunk Kultur",
        "Deutschlandfunk Nova",
    }
    assert {outlet["name"] for outlet in entries["RTL NEWS"]["outlets"]} == {
        "RTL Aktuell",
        "ntv",
        "RTL Radio / RTL Aktuell",
    }
    assert {outlet["name"] for outlet in entries[":newstime"]["outlets"]} == {
        ":newstime SAT.1",
        ":newstime ProSieben",
        ":newstime Kabel Eins",
    }
    assert entries["WELT"]["source_action"] == "extend_existing_source"
    assert entries["WELT"]["existing_source_key"] == "welt"

    source_names = set(entries)
    assert source_names.isdisjoint({
        "Deutschlandfunk",
        "Deutschlandfunk Kultur",
        "Deutschlandfunk Nova",
        "RTL Aktuell",
        "ntv",
        "RTL Radio",
        "SAT.1",
        "ProSieben",
        "Kabel Eins",
        "WELT TV",
    })


def test_de_national_broadcast_keeps_regional_sources_out() -> None:
    catalog = load_de_broadcast_catalog()
    names = {
        entry["name"]
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    assert names.isdisjoint({
        "BR24",
        "NDR Info",
        "WDR 5",
        "SWR Aktuell",
        "MDR AKTUELL",
        "rbb24 Inforadio",
        "hr-iNFO",
        "ANTENNE BAYERN",
        "HIT RADIO FFH",
        "R.SH",
        "Radio Dreyeckland",
        "FSK Hamburg",
        "Radio CORAX",
        "Radio Blau",
        "Radio LORA München",
    })


def test_de_national_broadcast_sparse_segments_document_real_market_gaps() -> None:
    catalog = load_de_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}
    for key in ("radical_left", "left_liberal", "liberal_centre", "conservative", "right", "radical_right"):
        radio_count = sum(
            any(outlet["publication_form"] == "radio" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        tv_count = sum(
            any(outlet["publication_form"] == "television" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        if radio_count < catalog["coverage_targets"]["radio_min"] or tv_count < catalog["coverage_targets"]["television_min"]:
            assert groups[key].get("coverage_exception")


def test_de_national_broadcast_two_source_status_has_independent_provenance() -> None:
    catalog = load_de_broadcast_catalog()
    entries = [entry for group in catalog["groups"] for entry in group["entries"]]
    confirmed = [
        entry for entry in entries
        if entry["classification_status"] == "two_source_direction_confirmed"
    ]
    assert {entry["name"] for entry in confirmed} == {"WELT", "Kontrafunk", "NIUS"}
    for entry in confirmed:
        orientation_sources = {
            item["classifier_name"]
            for item in entry["classifications"]
            if item["dimension"] == "editorial_orientation"
        }
        assert len(orientation_sources) >= 2


def test_de_national_broadcast_religious_identity_is_not_political_classification() -> None:
    catalog = load_de_broadcast_catalog()
    entries = {
        entry["name"]: entry
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    for name in ("IDEA", "EWTN Deutschland", "Hope TV Deutsch", "ERF", "radio horeb"):
        assert entries[name]["classification_status"] == "thematic_candidate_not_political_classification"

    for name in ("IDEA", "EWTN Deutschland", "Hope TV Deutsch", "ERF", "radio horeb"):
        assert not any(
            item["dimension"] == "editorial_orientation"
            for item in entries[name]["classifications"]
        )


def test_de_national_broadcast_defers_non_linear_cases() -> None:
    catalog = load_de_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert "phoenix" not in deferred
    assert {"Deutsche Welle", "BILD TV"} <= set(deferred)


def test_de_national_broadcast_phoenix_is_own_nonpolitical_source() -> None:
    catalog = load_de_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}
    phoenix = next(entry for entry in groups["liberal_centre"]["entries"] if entry["key"] == "phoenix")
    assert phoenix["name"] == "phoenix"
    assert phoenix["classification_status"] == "public_service_reference_not_political_classification"
    assert phoenix["classifications"] == []
    assert {outlet["name"] for outlet in phoenix["outlets"]} == {"phoenix"}
    assert any("no static collapsing SourceRelation" in note for note in phoenix["notes"])


AT_BROADCAST_CATALOG = CATALOG_DIR / "at_broadcast_v1.json"


def load_at_broadcast_catalog() -> dict:
    return json.loads(AT_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def at_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_at_national_broadcast_catalog_has_approved_editorial_sources() -> None:
    catalog = load_at_broadcast_catalog()
    assert catalog["country"] == "AT"
    assert catalog["scope"] == "national"
    assert catalog["media_category"] == "broadcast"
    assert catalog["activation_policy"] == "catalog_only_until_joint_review"
    assert catalog["source_identity_policy"] == "one_editorial_source_multiple_programmes_and_channels_as_outlets"
    assert catalog["approved_candidate_count"] == 8
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"

    entries = at_broadcast_entries(catalog)
    assert len(entries) == 8
    assert len({entry["key"] for entry in entries}) == 8
    assert len({entry["name"].casefold() for entry in entries}) == 8
    assert all(entry["catalog_status"] == "candidate" for entry in entries)
    assert all(entry["activity_status"] == "active" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)
    assert all(entry["outlets"] for entry in entries)
    assert all(
        outlet["publication_form"] in {"radio", "television"}
        for entry in entries
        for outlet in entry["outlets"]
    )


def test_at_national_broadcast_deduplicates_crossmedia_newsrooms() -> None:
    catalog = load_at_broadcast_catalog()
    entries = {entry["name"]: entry for entry in at_broadcast_entries(catalog)}

    assert {outlet["name"] for outlet in entries["ORF Information"]["outlets"]} == {
        "ORF 1",
        "ORF 2",
        "ORF III",
        "Ö1",
        "Ö3",
        "FM4",
    }
    assert {outlet["name"] for outlet in entries["ProSiebenSat.1 PULS 4 Newsroom"]["outlets"]} == {
        "PULS 24",
        "PULS 4",
        "ATV",
    }
    assert {outlet["name"] for outlet in entries["ÖSTERREICH / oe24"]["outlets"]} == {
        "oe24.TV",
        "oe24 RADIO",
    }
    assert entries["ÖSTERREICH / oe24"]["source_action"] == "extend_existing_source"
    assert entries["ÖSTERREICH / oe24"]["existing_source_key"] == "oesterreich-oe24"

    source_names = set(entries)
    assert source_names.isdisjoint({
        "ORF 1",
        "ORF 2",
        "ORF III",
        "Ö1",
        "Ö3",
        "FM4",
        "PULS 24",
        "PULS 4",
        "ATV",
        "oe24.TV",
        "oe24 RADIO",
    })


def test_at_national_broadcast_keeps_oe24_unclassified_until_provenance() -> None:
    catalog = load_at_broadcast_catalog()
    grouped_names = {
        entry["name"]
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    unclassified = {entry["name"]: entry for entry in catalog["unclassified_entries"]}

    assert "ÖSTERREICH / oe24" not in grouped_names
    assert set(unclassified) == {"ÖSTERREICH / oe24"}
    assert unclassified["ÖSTERREICH / oe24"]["classification_status"] == "unclassified_research_candidate"
    assert unclassified["ÖSTERREICH / oe24"]["classifications"] == []


def test_at_national_broadcast_keeps_regional_sources_out() -> None:
    catalog = load_at_broadcast_catalog()
    names = {entry["name"] for entry in at_broadcast_entries(catalog)}
    assert names.isdisjoint({
        "Radio Wien",
        "Radio Niederösterreich",
        "Radio Oberösterreich",
        "Radio Steiermark",
        "Radio Tirol",
        "Radio Vorarlberg",
        "W24",
        "Antenne Steiermark",
        "Life Radio",
    })


def test_at_national_broadcast_sparse_segments_document_real_market_gaps() -> None:
    catalog = load_at_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}
    for key in ("radical_left", "left_liberal", "liberal_centre", "conservative", "right", "radical_right"):
        radio_count = sum(
            any(outlet["publication_form"] == "radio" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        tv_count = sum(
            any(outlet["publication_form"] == "television" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        if radio_count < catalog["coverage_targets"]["radio_min"] or tv_count < catalog["coverage_targets"]["television_min"]:
            assert groups[key].get("coverage_exception")


def test_at_national_broadcast_two_source_status_has_independent_provenance() -> None:
    catalog = load_at_broadcast_catalog()
    confirmed = [
        entry for entry in at_broadcast_entries(catalog)
        if entry["classification_status"] == "two_source_direction_confirmed"
    ]
    assert {entry["name"] for entry in confirmed} == {"AUF1"}
    for entry in confirmed:
        orientation_sources = {
            item["classifier_name"]
            for item in entry["classifications"]
            if item["dimension"] == "editorial_orientation"
        }
        assert len(orientation_sources) >= 2


def test_at_national_broadcast_religious_identity_is_not_political_classification() -> None:
    catalog = load_at_broadcast_catalog()
    entries = {entry["name"]: entry for entry in at_broadcast_entries(catalog)}
    radio_maria = entries["Radio Maria Österreich"]
    assert radio_maria["classification_status"] == "thematic_candidate_not_political_classification"
    assert not any(
        item["dimension"] == "editorial_orientation"
        for item in radio_maria["classifications"]
    )


def test_at_national_broadcast_classification_provenance_is_complete() -> None:
    catalog = load_at_broadcast_catalog()
    for entry in at_broadcast_entries(catalog):
        for classification in entry["classifications"]:
            assert classification["dimension"]
            assert classification["value"]
            assert classification["classifier_type"]
            assert classification["classifier_name"]
            assert classification["source_url"].startswith("https://")
            assert classification["reference_date"]
            assert classification["retrieved_at"]


def test_at_national_broadcast_defers_non_austrian_or_crossmedia_edge_cases() -> None:
    catalog = load_at_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}

    assert {"ERF Süd", "Kontrafunk", "Klassik Radio", "Krone.tv"} <= set(deferred)
    assert "predominantly from South Tyrol and Germany" in deferred["ERF Süd"]
    assert "duplicate Austrian Source" in deferred["Kontrafunk"]
    assert "existing German editorial Source" in deferred["Klassik Radio"]
    assert "existing Kronen Zeitung Source" in deferred["Krone.tv"]


CH_BROADCAST_CATALOG = CATALOG_DIR / "ch_broadcast_v1.json"


def load_ch_broadcast_catalog() -> dict:
    return json.loads(CH_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def ch_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_ch_national_broadcast_catalog_has_approved_editorial_sources() -> None:
    catalog = load_ch_broadcast_catalog()
    assert catalog["country"] == "CH"
    assert catalog["scope"] == "national"
    assert catalog["media_category"] == "broadcast"
    assert set(catalog["languages"]) == {"de", "fr", "it", "rm"}
    assert catalog["activation_policy"] == "catalog_only_until_joint_review"
    assert catalog["approved_candidate_count"] == 13
    assert catalog["new_source_count"] == 8
    assert catalog["existing_source_extension_or_reuse_count"] == 5
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"

    entries = ch_broadcast_entries(catalog)
    assert len(entries) == 13
    assert sum(entry["source_action"] == "create_source" for entry in entries) == 8
    assert sum(entry["source_action"] in {"extend_existing_source", "reuse_existing_source"} for entry in entries) == 5
    assert len({entry["key"] for entry in entries}) == 13
    assert len({entry["name"].casefold() for entry in entries}) == 13
    assert all(entry["catalog_status"] == "candidate" for entry in entries)
    assert all(entry["activity_status"] == "active" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)
    assert all(entry["outlets"] for entry in entries)
    assert all(
        outlet["publication_form"] in {"radio", "television"}
        for entry in entries
        for outlet in entry["outlets"]
    )


def test_ch_srg_language_regions_are_four_editorial_sources() -> None:
    catalog = load_ch_broadcast_catalog()
    entries = {entry["name"]: entry for entry in ch_broadcast_entries(catalog)}

    assert {"SRF", "RTS", "RSI", "RTR"} <= set(entries)
    assert all(entries[name]["source_action"] == "create_source" for name in ("SRF", "RTS", "RSI", "RTR"))
    assert all(entries[name]["outlets"] for name in ("SRF", "RTS", "RSI", "RTR"))
    assert "SRG SSR" not in entries
    assert entries["SRF"]["classification_status"] == "public_service_centre_reference_not_political_classification"
    assert entries["RTS"]["classification_status"] == "public_service_centre_reference_not_political_classification"
    assert entries["RSI"]["classification_status"] == "unclassified_research_candidate"
    assert entries["RTR"]["classification_status"] == "unclassified_research_candidate"


def test_ch_pressetv_formats_extend_existing_editorial_sources() -> None:
    catalog = load_ch_broadcast_catalog()
    entries = {entry["name"]: entry for entry in ch_broadcast_entries(catalog)}

    assert entries["SonntagsZeitung"]["existing_source_key"] == "sonntagszeitung"
    assert entries["Neue Zürcher Zeitung"]["existing_source_key"] == "nzz"
    assert entries["BILANZ"]["existing_source_key"] == "bilanz"
    assert entries["Blick"]["existing_source_key"] == "blick"
    assert {outlet["name"] for outlet in entries["Neue Zürcher Zeitung"]["outlets"]} == {
        "NZZ Format",
        "NZZ Standpunkte",
    }
    assert {outlet["name"] for outlet in entries["SonntagsZeitung"]["outlets"]} == {
        "SonntagsZeitung Standpunkte",
    }
    assert {outlet["name"] for outlet in entries["BILANZ"]["outlets"]} == {
        "BILANZ Standpunkte",
    }
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert "PresseTV" in deferred
    assert "content responsibility" in deferred["PresseTV"]


def test_ch_fenster_zum_sonntag_has_two_editorial_sources() -> None:
    catalog = load_ch_broadcast_catalog()
    entries = {entry["name"]: entry for entry in ch_broadcast_entries(catalog)}

    assert {outlet["name"] for outlet in entries["ALPHAVISION"]["outlets"]} == {
        "FENSTER ZUM SONNTAG Magazin",
    }
    assert {outlet["name"] for outlet in entries["ERF Medien Schweiz"]["outlets"]} == {
        "FENSTER ZUM SONNTAG Talk",
        "Radio Life Channel",
    }
    for name in ("ALPHAVISION", "ERF Medien Schweiz", "Radio Maria Deutschschweiz"):
        assert entries[name]["classification_status"] == "thematic_candidate_not_political_classification"
        assert not any(
            item["dimension"] == "editorial_orientation"
            for item in entries[name]["classifications"]
        )


def test_ch_kontrafunk_reuses_existing_crossborder_source() -> None:
    catalog = load_ch_broadcast_catalog()
    entries = {entry["name"]: entry for entry in ch_broadcast_entries(catalog)}
    kontrafunk = entries["Kontrafunk"]

    assert kontrafunk["source_action"] == "reuse_existing_source"
    assert kontrafunk["existing_source_key"] == "kontrafunk"
    assert kontrafunk["existing_catalog"] == "de_broadcast_v1.json"


def test_ch_national_broadcast_two_source_status_has_independent_provenance() -> None:
    catalog = load_ch_broadcast_catalog()
    confirmed = [
        entry for entry in ch_broadcast_entries(catalog)
        if entry["classification_status"] == "two_source_direction_confirmed"
    ]
    assert {entry["name"] for entry in confirmed} == {
        "SonntagsZeitung",
        "Neue Zürcher Zeitung",
        "Kontrafunk",
        "Kla.TV",
    }
    for entry in confirmed:
        orientation_sources = {
            item["classifier_name"]
            for item in entry["classifications"]
            if item["dimension"] == "editorial_orientation"
        }
        assert len(orientation_sources) >= 2


def test_ch_national_broadcast_sparse_segments_document_real_market_gaps() -> None:
    catalog = load_ch_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}
    for key in ("radical_left", "left_liberal", "liberal_centre", "conservative", "right", "radical_right"):
        radio_count = sum(
            any(outlet["publication_form"] == "radio" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        tv_count = sum(
            any(outlet["publication_form"] == "television" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        if radio_count < catalog["coverage_targets"]["radio_min"] or tv_count < catalog["coverage_targets"]["television_min"]:
            assert groups[key].get("coverage_exception")


def test_ch_national_broadcast_keeps_regional_sources_out() -> None:
    catalog = load_ch_broadcast_catalog()
    names = {entry["name"] for entry in ch_broadcast_entries(catalog)}
    assert names.isdisjoint({
        "TeleBärn",
        "TeleBasel",
        "Tele M1",
        "TVO",
        "TeleTicino",
        "Radio RaBe",
        "Kanal K",
    })


def test_ch_national_broadcast_defers_non_source_or_wrong_medium_cases() -> None:
    catalog = load_ch_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert {
        "PresseTV",
        "Südostschweiz Standpunkte",
        "3+ sender family",
        "Weltwoche Daily",
        "licensed local radio and regional television",
    } <= set(deferred)
    assert "Transmission/project company" in deferred["PresseTV"]
    assert "digital-video/podcast block" in deferred["Weltwoche Daily"]


def test_ch_national_broadcast_classification_provenance_is_complete() -> None:
    catalog = load_ch_broadcast_catalog()
    for entry in ch_broadcast_entries(catalog):
        for classification in entry["classifications"]:
            assert classification["dimension"]
            assert classification["value"]
            assert classification["classifier_type"]
            assert classification["classifier_name"]
            assert classification["source_url"].startswith("https://")
            assert classification["reference_date"]
            assert classification["retrieved_at"]


GB_BROADCAST_CATALOG = CATALOG_DIR / "gb_broadcast_v1.json"


def load_gb_broadcast_catalog() -> dict:
    return json.loads(GB_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def gb_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_gb_national_broadcast_catalog_has_approved_editorial_sources() -> None:
    catalog = load_gb_broadcast_catalog()
    assert catalog["country"] == "GB"
    assert catalog["scope"] == "national"
    assert catalog["media_category"] == "broadcast"
    assert catalog["approved_candidate_count"] == 14
    assert catalog["new_source_count"] == 14
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"

    entries = gb_broadcast_entries(catalog)
    assert len(entries) == 14
    assert len({entry["key"] for entry in entries}) == 14
    assert len({entry["name"].casefold() for entry in entries}) == 14
    assert all(entry["source_action"] == "create_source" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)


def test_gb_itn_newsrooms_remain_editorially_distinct_sources() -> None:
    catalog = load_gb_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_broadcast_entries(catalog)}

    assert {"ITV News", "Channel 4 News", "5 News"} <= set(entries)
    assert len({entries[name]["key"] for name in ("ITV News", "Channel 4 News", "5 News")}) == 3
    assert "ITN" not in entries


def test_gb_bbc_news_and_radio_5_live_are_separate_sources() -> None:
    catalog = load_gb_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_broadcast_entries(catalog)}

    assert entries["BBC News"]["key"] == "bbc-news"
    assert entries["BBC Radio 5 Live"]["key"] == "bbc-radio-5-live"
    assert entries["BBC News"]["key"] != entries["BBC Radio 5 Live"]["key"]
    assert any(outlet["name"] == "Today" for outlet in entries["BBC News"]["outlets"])
    assert any(outlet["name"] == "BBC Radio 5 Live" for outlet in entries["BBC Radio 5 Live"]["outlets"])


def test_gb_lbc_and_lbc_news_are_separate_sources() -> None:
    catalog = load_gb_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_broadcast_entries(catalog)}

    assert entries["LBC"]["key"] == "lbc"
    assert entries["LBC News"]["key"] == "lbc-news"
    assert entries["LBC"]["key"] != entries["LBC News"]["key"]
    assert entries["LBC"]["classification_status"] == "unclassified_research_candidate"
    assert entries["LBC News"]["classification_status"] == "unclassified_research_candidate"


def test_gb_times_radio_is_not_an_outlet_of_the_times_source() -> None:
    catalog = load_gb_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_broadcast_entries(catalog)}
    times_radio = entries["Times Radio"]

    assert times_radio["source_action"] == "create_source"
    assert times_radio["related_existing_source_key"] == "times"
    assert times_radio["classification_status"] == "unclassified_research_candidate"


def test_gb_news_is_one_crossmedia_source() -> None:
    catalog = load_gb_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_broadcast_entries(catalog)}
    gb_news = entries["GB News"]

    assert {outlet["name"] for outlet in gb_news["outlets"]} == {"GB News", "GB News Radio"}
    assert {outlet["publication_form"] for outlet in gb_news["outlets"]} == {"television", "radio"}


def test_gb_ucb_programmes_are_outlets_of_one_source() -> None:
    catalog = load_gb_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_broadcast_entries(catalog)}

    assert {outlet["name"] for outlet in entries["UCB"]["outlets"]} == {"UCB 1", "UCB 2"}
    assert "UCB 1" not in entries
    assert "UCB 2" not in entries


def test_gb_national_broadcast_two_source_status_has_independent_provenance() -> None:
    catalog = load_gb_broadcast_catalog()
    confirmed = [
        entry for entry in gb_broadcast_entries(catalog)
        if entry["classification_status"] == "two_source_direction_confirmed"
    ]
    assert {entry["name"] for entry in confirmed} == {"Channel 4 News", "GB News"}

    for entry in confirmed:
        orientation_sources = {
            item["classifier_name"]
            for item in entry["classifications"]
            if item["dimension"] == "editorial_orientation"
        }
        assert len(orientation_sources) >= 2


def test_gb_religious_sources_are_not_politically_classified() -> None:
    catalog = load_gb_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_broadcast_entries(catalog)}

    for name in ("Revelation TV", "UCB", "Premier Christian Radio"):
        assert entries[name]["classification_status"] == "thematic_candidate_not_political_classification"
        assert not any(
            item["dimension"] == "editorial_orientation"
            for item in entries[name]["classifications"]
        )


def test_gb_sparse_segments_document_real_market_gaps() -> None:
    catalog = load_gb_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}

    for key in ("radical_left", "left_liberal", "liberal_centre", "conservative", "right", "radical_right"):
        radio_count = sum(
            any(outlet["publication_form"] == "radio" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        tv_count = sum(
            any(outlet["publication_form"] == "television" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        if radio_count < catalog["coverage_targets"]["radio_min"] or tv_count < catalog["coverage_targets"]["television_min"]:
            assert groups[key].get("coverage_exception")


def test_gb_supplier_and_wrong_medium_cases_are_deferred() -> None:
    catalog = load_gb_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}

    assert "Sky News Radio" in deferred
    assert "Agency/Content Supplier" in deferred["Sky News Radio"]
    assert "Novara Media" in deferred
    assert "digital-video/podcast block" in deferred["Novara Media"]
    assert "former TalkTV linear channel" in deferred


def test_gb_regional_and_devolved_sources_are_not_in_national_core() -> None:
    catalog = load_gb_broadcast_catalog()
    names = {entry["name"] for entry in gb_broadcast_entries(catalog)}

    assert names.isdisjoint({
        "BBC Local Radio",
        "STV",
        "S4C",
    })


def test_gb_national_broadcast_classification_provenance_is_complete() -> None:
    catalog = load_gb_broadcast_catalog()
    for entry in gb_broadcast_entries(catalog):
        for classification in entry["classifications"]:
            assert classification["dimension"]
            assert classification["value"]
            assert classification["classifier_type"]
            assert classification["classifier_name"]
            assert classification["source_url"].startswith("https://")
            assert classification["reference_date"]
            assert classification["retrieved_at"]


US_BROADCAST_CATALOG = CATALOG_DIR / "us_broadcast_v1.json"


def load_us_broadcast_catalog() -> dict:
    return json.loads(US_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def us_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_us_national_broadcast_catalog_has_approved_editorial_sources() -> None:
    catalog = load_us_broadcast_catalog()
    assert catalog["country"] == "US"
    assert catalog["scope"] == "national"
    assert catalog["media_category"] == "broadcast"
    assert catalog["approved_candidate_count"] == 17
    assert catalog["new_source_count"] == 17
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"

    entries = us_broadcast_entries(catalog)
    assert len(entries) == 17
    assert len({entry["key"] for entry in entries}) == 17
    assert len({entry["name"].casefold() for entry in entries}) == 17
    assert all(entry["source_action"] == "create_source" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)


def test_us_crossmedia_sources_are_not_duplicated_by_medium() -> None:
    catalog = load_us_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_broadcast_entries(catalog)}

    assert {outlet["publication_form"] for outlet in entries["Democracy Now!"]["outlets"]} == {
        "television",
        "radio",
    }
    assert {outlet["publication_form"] for outlet in entries["EWTN"]["outlets"]} == {
        "television",
        "radio",
    }
    assert "Democracy Now! radio" not in entries
    assert "EWTN Radio" not in entries


def test_us_npr_programmes_are_outlets_of_one_source() -> None:
    catalog = load_us_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_broadcast_entries(catalog)}
    npr = entries["NPR"]

    assert {outlet["name"] for outlet in npr["outlets"]} == {
        "Morning Edition",
        "All Things Considered",
        "Weekend Edition",
    }
    assert "Morning Edition" not in entries
    assert "All Things Considered" not in entries


def test_us_siriusxm_political_channels_are_distinct_sources() -> None:
    catalog = load_us_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_broadcast_entries(catalog)}

    assert {
        "SiriusXM POTUS",
        "SiriusXM Progress",
        "SiriusXM Patriot",
    } <= set(entries)
    assert len({
        entries["SiriusXM POTUS"]["key"],
        entries["SiriusXM Progress"]["key"],
        entries["SiriusXM Patriot"]["key"],
    }) == 3
    assert entries["SiriusXM Progress"]["classification_status"] == "self_positioned_not_independently_confirmed"
    assert entries["SiriusXM Patriot"]["classification_status"] == "self_positioned_not_independently_confirmed"


def test_us_newsmax_right_direction_is_confirmed_but_radicality_unresolved() -> None:
    catalog = load_us_broadcast_catalog()
    grouped_names = {
        entry["name"]
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    entries = {entry["name"]: entry for entry in us_broadcast_entries(catalog)}
    newsmax = entries["Newsmax"]

    assert "Newsmax" not in grouped_names
    assert newsmax["classification_status"] == "right_direction_confirmed_radicality_unresolved"
    assert {
        item["value"]
        for item in newsmax["classifications"]
        if item["dimension"] == "editorial_orientation"
    } == {"right"}
    assert {
        item["value"]
        for item in newsmax["classifications"]
        if item["dimension"] == "radicality_positioning"
    } == {"far_right_outlet"}


def test_us_confirmed_direction_sources_have_independent_provenance() -> None:
    catalog = load_us_broadcast_catalog()
    entries = us_broadcast_entries(catalog)
    confirmed = [
        entry for entry in entries
        if entry["classification_status"] == "two_source_direction_confirmed"
    ]
    assert {entry["name"] for entry in confirmed} == {
        "Democracy Now!",
        "PBS NewsHour",
        "MS NOW",
        "CNN",
        "NPR",
        "Fox News",
    }

    for entry in confirmed:
        orientation_sources = {
            item["classifier_name"]
            for item in entry["classifications"]
            if item["dimension"] == "editorial_orientation"
        }
        assert len(orientation_sources) >= 2


def test_us_oan_far_right_status_has_two_independent_sources() -> None:
    catalog = load_us_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_broadcast_entries(catalog)}
    oan = entries["One America News"]

    assert oan["classification_status"] == "two_source_radicality_confirmed"
    assert len({
        item["classifier_name"]
        for item in oan["classifications"]
        if item["dimension"] == "editorial_orientation"
    }) >= 2


def test_us_religious_sources_are_not_politically_classified() -> None:
    catalog = load_us_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_broadcast_entries(catalog)}

    for name in ("EWTN", "American Family Radio"):
        assert entries[name]["classification_status"] == "thematic_candidate_not_political_classification"
        assert not any(
            item["dimension"] == "editorial_orientation"
            for item in entries[name]["classifications"]
        )


def test_us_supplier_simulcast_and_specialist_cases_are_deferred() -> None:
    catalog = load_us_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}

    assert "ABC News Radio" in deferred
    assert "Agency/Content Supplier" in deferred["ABC News Radio"]
    assert "Fox News Radio" in deferred
    assert "Agency/Content Supplier" in deferred["Fox News Radio"]
    assert "CBS News Radio" in deferred
    assert "ended on May 22, 2026" in deferred["CBS News Radio"]

    for name in ("CNN SiriusXM simulcast", "Fox News SiriusXM simulcast", "MS NOW SiriusXM simulcast"):
        assert "does not create a separate radio Source" in deferred[name]

    assert {"CNBC", "Bloomberg Television / Radio", "Fox Business"} <= set(deferred)


def test_us_regional_sources_are_not_in_national_core() -> None:
    catalog = load_us_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert "local network affiliates and public-media stations" in deferred
    assert "US regional block" in deferred["local network affiliates and public-media stations"]


def test_us_sparse_segments_document_real_market_gaps() -> None:
    catalog = load_us_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}

    for key in ("radical_left", "left_liberal", "liberal_centre", "conservative", "right", "radical_right"):
        radio_count = sum(
            any(outlet["publication_form"] == "radio" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        tv_count = sum(
            any(outlet["publication_form"] == "television" for outlet in entry["outlets"])
            for entry in groups[key]["entries"]
        )
        if radio_count < catalog["coverage_targets"]["radio_min"] or tv_count < catalog["coverage_targets"]["television_min"]:
            assert groups[key].get("coverage_exception")


def test_us_national_broadcast_classification_provenance_is_complete() -> None:
    catalog = load_us_broadcast_catalog()
    for entry in us_broadcast_entries(catalog):
        for classification in entry["classifications"]:
            assert classification["dimension"]
            assert classification["value"]
            assert classification["classifier_type"]
            assert classification["classifier_name"]
            assert classification["source_url"].startswith("https://")
            assert classification["reference_date"]
            assert classification["retrieved_at"]


DE_REGIONAL_BROADCAST_CATALOG = CATALOG_DIR / "de_regional_broadcast_v1.json"


def load_de_regional_broadcast_catalog() -> dict:
    return json.loads(DE_REGIONAL_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def de_regional_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_de_regional_broadcast_catalog_has_approved_editorial_sources() -> None:
    catalog = load_de_regional_broadcast_catalog()
    assert catalog["country"] == "DE"
    assert catalog["scope"] == "regional"
    assert catalog["media_category"] == "broadcast"
    assert catalog["approved_candidate_count"] == 19
    assert catalog["new_source_count"] == 19
    assert catalog["activation_policy"] == "catalog_only_until_joint_review"
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"

    entries = de_regional_broadcast_entries(catalog)
    assert len(entries) == 19
    assert len({entry["key"] for entry in entries}) == 19
    assert len({entry["name"].casefold() for entry in entries}) == 19
    assert all(entry["source_action"] == "create_source" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)


def test_de_regional_broadcast_has_exactly_nine_ard_landesrundfunkanstalten() -> None:
    catalog = load_de_regional_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}
    centre = {entry["name"]: entry for entry in groups["liberal_centre"]["entries"]}

    assert set(centre) == {
        "Bayerischer Rundfunk",
        "Hessischer Rundfunk",
        "Mitteldeutscher Rundfunk",
        "Norddeutscher Rundfunk",
        "Radio Bremen",
        "Rundfunk Berlin-Brandenburg",
        "Saarländischer Rundfunk",
        "Südwestrundfunk",
        "Westdeutscher Rundfunk",
    }
    assert all(
        entry["classification_status"] == "public_service_centre_reference_not_political_classification"
        for entry in centre.values()
    )
    assert all(entry["classifications"] == [] for entry in centre.values())
    assert "ARD" not in centre


def test_de_regional_broadcast_public_service_programmes_are_outlets() -> None:
    catalog = load_de_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in de_regional_broadcast_entries(catalog)}

    assert {outlet["name"] for outlet in entries["Bayerischer Rundfunk"]["outlets"]} == {
        "BR Fernsehen",
        "BR24",
        "Bayern 1",
        "Bayern 2",
    }
    assert {outlet["name"] for outlet in entries["Norddeutscher Rundfunk"]["outlets"]} == {
        "NDR Fernsehen",
        "NDR Info",
        "NDR 1 Niedersachsen",
    }
    assert "BR Fernsehen" not in entries
    assert "NDR Info" not in entries


def test_de_regional_broadcast_north_regional_windows_are_deduplicated() -> None:
    catalog = load_de_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in de_regional_broadcast_entries(catalog)}

    assert {outlet["name"] for outlet in entries["RTL Nord"]["outlets"]} == {
        "RTL Nord Hamburg/Schleswig-Holstein",
        "RTL Nord Niedersachsen/Bremen",
    }
    assert {outlet["name"] for outlet in entries["SAT.1 Norddeutschland"]["outlets"]} == {
        "SAT.1 REGIONAL Hamburg/Schleswig-Holstein",
        "SAT.1 REGIONAL Niedersachsen/Bremen",
    }
    assert "RTL Nord Hamburg/Schleswig-Holstein" not in entries
    assert "SAT.1 REGIONAL Niedersachsen/Bremen" not in entries


def test_de_regional_broadcast_private_tv_sources_are_separate_from_national_newsrooms() -> None:
    catalog = load_de_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in de_regional_broadcast_entries(catalog)}

    for name in ("RTL Nord", "RTL WEST", "RTL Hessen", "SAT.1 Norddeutschland", "SAT.1 Bayern"):
        assert entries[name]["source_action"] == "create_source"
        assert entries[name]["classification_status"] == "unclassified_research_candidate"

    assert "RTL NEWS" not in entries
    assert ":newstime" not in entries


def test_de_regional_broadcast_ffh_newsroom_is_one_source() -> None:
    catalog = load_de_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in de_regional_broadcast_entries(catalog)}
    ffh = entries["FFH Newsredaktion"]

    assert {outlet["name"] for outlet in ffh["outlets"]} == {
        "HIT RADIO FFH",
        "planet radio",
        "harmony",
    }
    assert "HIT RADIO FFH" not in entries
    assert "planet radio" not in entries
    assert "harmony" not in entries


def test_de_regional_broadcast_rsh_is_source_regiocast_news_is_supplier() -> None:
    catalog = load_de_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in de_regional_broadcast_entries(catalog)}
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}

    assert "R.SH" in entries
    assert entries["R.SH"]["classification_status"] == "unclassified_research_candidate"
    assert "REGIOCAST Nachrichten" not in entries
    assert "REGIOCAST Nachrichten" in deferred
    assert "Agency/Content Supplier" in deferred["REGIOCAST Nachrichten"]


def test_de_regional_broadcast_private_sources_remain_unclassified() -> None:
    catalog = load_de_regional_broadcast_catalog()
    unclassified = {entry["name"]: entry for entry in catalog["unclassified_entries"]}

    assert set(unclassified) == {
        "RTL Nord",
        "RTL WEST",
        "RTL Hessen",
        "SAT.1 Norddeutschland",
        "SAT.1 Bayern",
        "ANTENNE BAYERN",
        "FFH Newsredaktion",
        "radio ffn",
        "R.SH",
        "radio SAW",
    }
    assert all(
        entry["classification_status"] == "unclassified_research_candidate"
        for entry in unclassified.values()
    )
    assert all(entry["classifications"] == [] for entry in unclassified.values())


def test_de_regional_broadcast_local_media_are_deferred() -> None:
    catalog = load_de_regional_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}

    assert "local television" in deferred
    assert "DE local block" in deferred["local television"]
    assert "local radio" in deferred
    assert "DE local block" in deferred["local radio"]
    assert "Antenne Niedersachsen" in deferred


def test_de_regional_broadcast_sparse_segments_document_real_market_gaps() -> None:
    catalog = load_de_regional_broadcast_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}

    for key in ("radical_left", "left_liberal", "conservative", "right", "radical_right"):
        assert groups[key]["entries"] == []
        assert groups[key].get("coverage_exception")

    assert len(groups["liberal_centre"]["entries"]) == 9


def test_de_regional_broadcast_outlet_keys_are_unique() -> None:
    catalog = load_de_regional_broadcast_catalog()
    entries = de_regional_broadcast_entries(catalog)
    outlet_keys = [
        outlet["key"]
        for entry in entries
        for outlet in entry["outlets"]
    ]
    assert len(outlet_keys) == len(set(outlet_keys))


AT_REGIONAL_BROADCAST_CATALOG = CATALOG_DIR / "at_regional_broadcast_v1.json"


def load_at_regional_broadcast_catalog() -> dict:
    return json.loads(AT_REGIONAL_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def at_regional_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_at_regional_broadcast_catalog_has_approved_editorial_sources() -> None:
    catalog = load_at_regional_broadcast_catalog()
    assert catalog["country"] == "AT"
    assert catalog["scope"] == "regional"
    assert catalog["approved_candidate_count"] == 19
    entries = at_regional_broadcast_entries(catalog)
    assert len(entries) == 19
    assert len({entry["key"] for entry in entries}) == 19
    assert all(entry["feeds"] == [] for entry in entries)


def test_at_regional_broadcast_has_nine_orf_landstudios() -> None:
    catalog = load_at_regional_broadcast_catalog()
    centre = {entry["name"]: entry for entry in next(g for g in catalog["groups"] if g["key"] == "liberal_centre")["entries"]}
    assert set(centre) == {
        "ORF Burgenland", "ORF Kärnten", "ORF Niederösterreich", "ORF Oberösterreich",
        "ORF Salzburg", "ORF Steiermark", "ORF Tirol", "ORF Vorarlberg", "ORF Wien",
    }
    assert all(len(entry["outlets"]) == 3 for entry in centre.values())
    assert all(entry["classification_status"] == "public_service_centre_reference_not_political_classification" for entry in centre.values())


def test_at_regional_broadcast_r9_does_not_merge_partner_sources() -> None:
    catalog = load_at_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in at_regional_broadcast_entries(catalog)}
    assert {"W24", "LT1", "Kanal3", "RTS Regionalfernsehen Salzburg", "Tirol TV"} <= set(entries)
    assert "R9" not in entries
    assert "R9" in {item["name"] for item in catalog["excluded_or_deferred"]}


def test_at_regional_broadcast_rtv_has_two_source_f_provenance() -> None:
    catalog = load_at_regional_broadcast_catalog()
    radical = next(g for g in catalog["groups"] if g["key"] == "radical_right")
    assert [entry["name"] for entry in radical["entries"]] == ["RTV Regionalfernsehen OÖ"]
    rtv = radical["entries"][0]
    assert rtv["classification_status"] == "two_source_extreme_right_spectrum_confirmed"
    assert len({item["classifier_name"] for item in rtv["classifications"]}) >= 2


def test_at_regional_broadcast_private_radio_sources_are_unclassified() -> None:
    catalog = load_at_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in catalog["unclassified_entries"]}
    for name in ("Antenne Steiermark", "Life Radio", "Radio U1 Tirol", "Radio 88.6"):
        assert entries[name]["classification_status"] == "unclassified_research_candidate"
        assert entries[name]["classifications"] == []


def test_at_regional_broadcast_kurier_tv_extends_existing_print_source_later() -> None:
    catalog = load_at_regional_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert "KURIER TV" in deferred
    assert "existing Kurier Source" in deferred["KURIER TV"]


def test_at_regional_broadcast_outlet_keys_are_unique() -> None:
    catalog = load_at_regional_broadcast_catalog()
    outlet_keys = [outlet["key"] for entry in at_regional_broadcast_entries(catalog) for outlet in entry["outlets"]]
    assert len(outlet_keys) == len(set(outlet_keys))


CH_REGIONAL_BROADCAST_CATALOG = CATALOG_DIR / "ch_regional_broadcast_v1.json"


def load_ch_regional_broadcast_catalog() -> dict:
    return json.loads(CH_REGIONAL_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def ch_regional_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_ch_regional_broadcast_catalog_has_compact_multilingual_core() -> None:
    catalog = load_ch_regional_broadcast_catalog()
    entries = ch_regional_broadcast_entries(catalog)
    assert catalog["country"] == "CH"
    assert catalog["scope"] == "regional"
    assert catalog["approved_candidate_count"] == 12
    assert len(entries) == 12
    assert len({entry["key"] for entry in entries}) == 12
    assert all(entry["classification_status"] == "unclassified_research_candidate" for entry in entries)


def test_ch_regional_broadcast_language_regions_are_represented_without_quota() -> None:
    catalog = load_ch_regional_broadcast_catalog()
    languages = {
        outlet["language"]
        for entry in ch_regional_broadcast_entries(catalog)
        for outlet in entry["outlets"]
    }
    assert {"de", "fr", "it"} <= languages


def test_ch_regional_broadcast_public_service_regional_output_is_not_duplicated() -> None:
    catalog = load_ch_regional_broadcast_catalog()
    names = {entry["name"] for entry in ch_regional_broadcast_entries(catalog)}
    assert names.isdisjoint({"SRF", "RTS", "RSI", "RTR"})
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert "existing SRF Source" in deferred["SRF regional journals"]
    assert "existing RTS Source" in deferred["RTS regional output"]


def test_ch_regional_broadcast_shared_ownership_does_not_merge_independent_tv_sources() -> None:
    catalog = load_ch_regional_broadcast_catalog()
    names = {entry["name"] for entry in ch_regional_broadcast_entries(catalog)}
    assert {"TeleBärn", "Tele M1", "TVO"} <= names


def test_ch_regional_broadcast_bilingual_services_are_single_sources() -> None:
    catalog = load_ch_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in ch_regional_broadcast_entries(catalog)}
    assert {outlet["name"] for outlet in entries["Canal 9 / Kanal 9"]["outlets"]} == {"Canal 9", "Kanal 9"}
    assert {outlet["name"] for outlet in entries["RadioFr. Fribourg/Freiburg"]["outlets"]} == {"RadioFr. Fribourg", "RadioFr. Freiburg"}


def test_ch_regional_broadcast_outlet_keys_are_unique() -> None:
    catalog = load_ch_regional_broadcast_catalog()
    keys = [outlet["key"] for entry in ch_regional_broadcast_entries(catalog) for outlet in entry["outlets"]]
    assert len(keys) == len(set(keys))


GB_REGIONAL_BROADCAST_CATALOG = CATALOG_DIR / "gb_regional_broadcast_v1.json"


def load_gb_regional_broadcast_catalog() -> dict:
    return json.loads(GB_REGIONAL_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def gb_regional_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_gb_regional_broadcast_catalog_has_six_devolved_sources() -> None:
    catalog = load_gb_regional_broadcast_catalog()
    entries = gb_regional_broadcast_entries(catalog)
    assert catalog["country"] == "GB"
    assert catalog["scope"] == "regional_devolved"
    assert catalog["approved_candidate_count"] == 6
    assert len(entries) == 6
    assert len({entry["key"] for entry in entries}) == 6


def test_gb_regional_broadcast_bbc_nations_are_three_crossmedia_sources() -> None:
    catalog = load_gb_regional_broadcast_catalog()
    centre = {entry["name"]: entry for entry in next(g for g in catalog["groups"] if g["key"] == "liberal_centre")["entries"]}
    assert set(centre) == {"BBC Scotland", "BBC Cymru Wales", "BBC Northern Ireland"}
    assert all({outlet["publication_form"] for outlet in entry["outlets"]} == {"television", "radio"} for entry in centre.values())
    assert all(entry["classification_status"] == "public_service_centre_reference_not_political_classification" for entry in centre.values())


def test_gb_regional_broadcast_private_devolved_tv_sources_are_separate() -> None:
    catalog = load_gb_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in gb_regional_broadcast_entries(catalog)}
    assert {"STV News", "ITV Cymru Wales", "UTV"} <= set(entries)
    assert entries["ITV Cymru Wales"]["classification_status"] == "unclassified_research_candidate"
    assert entries["UTV"]["classification_status"] == "unclassified_research_candidate"
    assert "ITV News" not in entries


def test_gb_regional_broadcast_s4c_news_is_not_duplicated() -> None:
    catalog = load_gb_regional_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert "S4C as a news Source" in deferred
    assert "produced by BBC Cymru Wales" in deferred["S4C as a news Source"]


def test_gb_regional_broadcast_joint_bbc_alba_is_deferred() -> None:
    catalog = load_gb_regional_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}
    assert "BBC ALBA" in deferred
    assert "joint" in deferred["BBC ALBA"].lower()


def test_gb_regional_broadcast_outlet_keys_are_unique() -> None:
    catalog = load_gb_regional_broadcast_catalog()
    keys = [outlet["key"] for entry in gb_regional_broadcast_entries(catalog) for outlet in entry["outlets"]]
    assert len(keys) == len(set(keys))


US_REGIONAL_BROADCAST_CATALOG = CATALOG_DIR / "us_regional_broadcast_v1.json"


def load_us_regional_broadcast_catalog() -> dict:
    return json.loads(US_REGIONAL_BROADCAST_CATALOG.read_text(encoding="utf-8"))


def us_regional_broadcast_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog.get("unclassified_entries", []),
    ]


def test_us_regional_broadcast_catalog_has_representative_core() -> None:
    catalog = load_us_regional_broadcast_catalog()
    entries = us_regional_broadcast_entries(catalog)

    assert catalog["country"] == "US"
    assert catalog["scope"] == "regional"
    assert catalog["approved_candidate_count"] == 10
    assert catalog["new_source_count"] == 10
    assert len(entries) == 10
    assert len({entry["key"] for entry in entries}) == 10
    assert all(entry["classification_status"] == "unclassified_research_candidate" for entry in entries)
    assert all(entry["classifications"] == [] for entry in entries)


def test_us_regional_broadcast_public_media_affiliation_does_not_merge_national_sources() -> None:
    catalog = load_us_regional_broadcast_catalog()
    names = {entry["name"] for entry in us_regional_broadcast_entries(catalog)}

    assert {
        "WNYC / Gothamist Newsroom",
        "WHYY News",
        "WBEZ Chicago",
        "WABE News",
        "KUT News",
        "KQED News",
        "LAist",
    } <= names
    assert "NPR" not in names
    assert "PBS" not in names


def test_us_regional_broadcast_wnyc_gothamist_is_one_source() -> None:
    catalog = load_us_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_regional_broadcast_entries(catalog)}
    assert {outlet["name"] for outlet in entries["WNYC / Gothamist Newsroom"]["outlets"]} == {
        "WNYC",
        "Gothamist",
    }
    assert "Gothamist" not in entries


def test_us_regional_broadcast_kut_texas_standard_is_one_source() -> None:
    catalog = load_us_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_regional_broadcast_entries(catalog)}
    assert {outlet["name"] for outlet in entries["KUT News"]["outlets"]} == {
        "KUT 90.5",
        "Texas Standard",
    }
    assert "Texas Standard" not in entries


def test_us_regional_broadcast_spectrum_newsrooms_remain_separate() -> None:
    catalog = load_us_regional_broadcast_catalog()
    entries = {entry["name"]: entry for entry in us_regional_broadcast_entries(catalog)}

    assert "Spectrum News NY1" in entries
    assert "Spectrum News 1 North Carolina" in entries
    assert entries["Spectrum News NY1"]["key"] != entries["Spectrum News 1 North Carolina"]["key"]


def test_us_regional_broadcast_network_affiliate_universe_is_deferred() -> None:
    catalog = load_us_regional_broadcast_catalog()
    deferred = {item["name"]: item["reason"] for item in catalog["excluded_or_deferred"]}

    assert "ABC/CBS/NBC/Fox local affiliates" in deferred
    assert "local-affiliate layer" in deferred["ABC/CBS/NBC/Fox local affiliates"]
    assert "Sinclair local television stations" in deferred
    assert "individual station/newsroom identity" in deferred["Sinclair local television stations"]


def test_us_regional_broadcast_outlet_keys_are_unique() -> None:
    catalog = load_us_regional_broadcast_catalog()
    keys = [
        outlet["key"]
        for entry in us_regional_broadcast_entries(catalog)
        for outlet in entry["outlets"]
    ]
    assert len(keys) == len(set(keys))

AGENCY_CONTENT_SUPPLIER_CATALOG = CATALOG_DIR / "agency_content_supplier_v1.json"


def load_agency_content_supplier_catalog() -> dict:
    return json.loads(AGENCY_CONTENT_SUPPLIER_CATALOG.read_text(encoding="utf-8"))


def test_agency_content_supplier_catalog_has_approved_core() -> None:
    catalog = load_agency_content_supplier_catalog()
    assert catalog["media_category"] == "agency_content_supplier"
    assert catalog["activation_policy"] == "catalog_only_until_joint_review"
    assert catalog["segmentation_policy"] == "functional_role_not_political_orientation"
    assert catalog["approved_candidate_count"] == 9
    assert catalog["provenance_policy"]["political_group_assignment"] == "two_independent_sources_required"

    entries = [entry for group in catalog["groups"] for entry in group["entries"]]
    assert len(entries) == 9
    assert {entry["name"] for entry in entries} == {
        "dpa",
        "dts Nachrichtenagentur",
        "APA",
        "Keystone-SDA",
        "PA Media",
        "Reuters",
        "Associated Press",
        "AFP",
        "REGIOCAST Nachrichten",
    }


def test_agency_catalog_is_functional_not_political() -> None:
    catalog = load_agency_content_supplier_catalog()
    entries = [entry for group in catalog["groups"] for entry in group["entries"]]
    assert all(entry["source_type"] == "AGENCY" for entry in entries)
    assert all(entry["classification_status"] == "functional_supplier_not_political_classification" for entry in entries)
    assert all(entry["classifications"] == [] for entry in entries)


def test_radio_supplier_services_extend_existing_editorial_sources() -> None:
    gb = json.loads((CATALOG_DIR / "gb_broadcast_v1.json").read_text(encoding="utf-8"))
    us = json.loads((CATALOG_DIR / "us_broadcast_v1.json").read_text(encoding="utf-8"))
    gb_entries = {entry["key"]: entry for group in gb["groups"] for entry in group["entries"]}
    us_entries = {entry["key"]: entry for group in us["groups"] for entry in group["entries"]}

    assert "Sky News Radio" in {outlet["name"] for outlet in gb_entries["sky-news"]["outlets"]}
    assert "ABC News Radio" in {outlet["name"] for outlet in us_entries["abc-news"]["outlets"]}
    assert "Fox News Radio" in {outlet["name"] for outlet in us_entries["fox-news"]["outlets"]}

    all_names = {
        entry["name"]
        for catalog in (gb, us)
        for group in catalog["groups"]
        for entry in group["entries"]
    }
    assert {"Sky News Radio", "ABC News Radio", "Fox News Radio"}.isdisjoint(all_names)


def test_regiocast_moves_from_de_broadcast_deferred_to_supplier_catalog() -> None:
    de = load_de_broadcast_catalog()
    deferred = {item["name"] for item in de["excluded_or_deferred"]}
    assert "REGIOCAST Nachrichten" not in deferred
    agency = load_agency_content_supplier_catalog()
    names = {entry["name"] for group in agency["groups"] for entry in group["entries"]}
    assert "REGIOCAST Nachrichten" in names


DE_DIGITAL_CATALOG = CATALOG_DIR / "de_digital_v1.json"


def load_de_digital_catalog() -> dict:
    return json.loads(DE_DIGITAL_CATALOG.read_text(encoding="utf-8"))


def de_digital_entries(catalog: dict) -> list[dict]:
    return [
        *[entry for group in catalog["groups"] for entry in group["entries"]],
        *catalog["unclassified_entries"],
    ]


def test_de_digital_catalog_has_approved_scope_and_counts() -> None:
    catalog = load_de_digital_catalog()
    assert catalog["country"] == "DE"
    assert catalog["media_category"] == "digital"
    assert catalog["activation_policy"] == "catalog_only_until_joint_review"
    assert catalog["source_identity_policy"] == "digital_is_medium_existing_cross_media_sources_are_extended_not_duplicated"
    assert catalog["publication_form_policy"] == "born_digital_sources_use_digital_native_existing_source_web_outlets_use_other"
    assert catalog["approved_candidate_count"] == 36
    assert catalog["approved_core_count"] == 29
    assert catalog["new_source_count"] == 20
    assert catalog["existing_source_extension_count"] == 16

    entries = de_digital_entries(catalog)
    assert len(entries) == 36
    assert len({entry["key"] for entry in entries}) == 36
    assert len({entry["name"].casefold() for entry in entries}) == 36
    assert all(entry["activity_status"] == "active" for entry in entries)
    assert all(entry["catalog_status"] == "candidate" for entry in entries)
    assert all(entry["feeds"] == [] for entry in entries)


def test_de_digital_planning_segments_match_approved_core() -> None:
    catalog = load_de_digital_catalog()
    groups = {group["key"]: group for group in catalog["groups"]}
    assert [len(groups[key]["entries"]) for key in (
        "radical_left", "left_liberal", "liberal_centre",
        "conservative", "right", "radical_right",
    )] == [5, 5, 5, 5, 5, 4]
    assert {
        entry["name"] for entry in groups["radical_left"]["entries"]
    } == {
        "Klasse Gegen Klasse", "Perspektive Online", "Lower Class Magazine",
        "NachDenkSeiten", "junge Welt",
    }
    assert {
        entry["name"] for entry in groups["right"]["entries"]
    } == {
        "Achgut", "Apollo News", "reitschuster.de", "NIUS", "Tichys Einblick",
    }


def test_de_digital_reuses_existing_cross_media_sources() -> None:
    catalog = load_de_digital_catalog()
    entries = de_digital_entries(catalog)
    extensions = [entry for entry in entries if entry["source_action"] == "extend_existing_source"]
    assert len(extensions) == 16
    assert {entry["existing_source_key"] for entry in extensions} == {
        "junge-welt", "taz", "der-spiegel", "die-zeit", "ard-aktuell", "zdf",
        "faz", "welt", "bild", "focus", "cicero", "nius", "tichys-einblick",
        "compact", "sezession", "zuerst",
    }
    assert all(
        outlet["media_category"] == "digital"
        and outlet["publication_form"] == "other"
        for entry in extensions
        for outlet in entry["outlets"]
    )


def test_de_digital_new_sources_are_digital_native() -> None:
    catalog = load_de_digital_catalog()
    entries = de_digital_entries(catalog)
    new_sources = [entry for entry in entries if entry["source_action"] == "create_source"]
    assert len(new_sources) == 20
    assert all(
        outlet["media_category"] == "digital"
        and outlet["publication_form"] == "digital_native"
        for entry in new_sources
        for outlet in entry["outlets"]
    )


def test_de_digital_unclassified_candidates_stay_outside_a_f() -> None:
    catalog = load_de_digital_catalog()
    assert {entry["name"] for entry in catalog["unclassified_entries"]} == {
        "netzpolitik.org", "Übermedien", "Table.Briefings", "Volksverpetzer",
        "Belltower.News", "Multipolar", "apolut",
    }
    assert all(
        entry["classification_status"] == "unclassified_research_candidate"
        and entry["classifications"] == []
        for entry in catalog["unclassified_entries"]
    )


def test_de_digital_planning_placement_does_not_persist_classification() -> None:
    catalog = load_de_digital_catalog()
    core = [entry for group in catalog["groups"] for entry in group["entries"]]
    assert all(entry["classifications"] == [] for entry in core)
    nachdenkseiten = next(entry for entry in core if entry["key"] == "nachdenkseiten")
    assert any("A/B research boundary" in note for note in nachdenkseiten["notes"])
    assert catalog["review_status"]["multipolar_apolut"] == "approved_unclassified"


def test_de_digital_extension_keys_exist_in_existing_de_catalogs() -> None:
    digital = load_de_digital_catalog()
    extensions = {
        entry["existing_source_key"]
        for entry in de_digital_entries(digital)
        if entry["source_action"] == "extend_existing_source"
    }
    existing_keys: set[str] = set()
    for filename in ("de_print_v1.json", "de_broadcast_v1.json"):
        catalog = json.loads((CATALOG_DIR / filename).read_text(encoding="utf-8"))
        existing_keys.update(
            entry["key"]
            for group in catalog["groups"]
            for entry in group["entries"]
        )
    assert extensions <= existing_keys
