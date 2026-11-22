"""VKF 14-15 reaction to fire of facades and linings: localized, cited, unreviewed (#90)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REGULATION_ID = "pragmaticbim:regulation/vkf-14-15-2015"


def _rules() -> list[tuple[Path, dict]]:
    return [
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted((REPO_ROOT / "rules").glob("vkf-14-15-*.yaml"))
    ]


def test_regulation_is_localized_swiss_2015() -> None:
    regulation = yaml.safe_load((REPO_ROOT / "regulations" / "vkf-14-15-2015.yaml").read_text(encoding="utf-8"))
    assert regulation["id"] == REGULATION_ID
    assert regulation["edition"] == "2015"
    assert regulation["jurisdiction"] == ["CH"]
    assert regulation["access"] == "free"
    for lang in LANGS:
        assert str(regulation["name"].get(lang) or "").strip(), lang


def test_rules_cover_facades_and_linings() -> None:
    quotes = " ".join(rule["rule_source"]["source_quote"] for _, rule in _rules())
    for clause in ("3.1.1", "3.1.2", "3.2.2", "3.2.3", "3.2.4", "3.2.7", "3.2.8", "4.1", "4.2"):
        assert f"Ziff. {clause}" in quotes, clause


def test_rules_are_localized_cited_and_unreviewed() -> None:
    rules = _rules()
    assert len(rules) >= 10
    for path, rule in rules:
        assert rule["rule_source"]["regulation"] == REGULATION_ID, path
        assert rule["rule_source"]["source_quote"].startswith("VKF 14-15, Ziff. "), path
        assert rule["rule_status"] == "reviewed", path
        assert rule["reviewed_by"] in (None, ""), path
        assert rule["reviewed_at"] in (None, ""), path
        assert rule["jurisdiction"] == ["ch"], path
        assert rule["edition"] == "2015", path
        for field in ("name", "description"):
            for lang in LANGS:
                assert str(rule[field].get(lang) or "").strip(), f"{path}: {field}.{lang}"


def test_rules_claim_no_performance_property_keys() -> None:
    for path, rule in _rules():
        # The rules stay text-only (reviewed) until the data contract maps RF-only values (#121), so no rule claims a key.
        assert "performance_property_keys" not in rule, path


def test_rules_apply_to_existing_elements() -> None:
    elements = {p.stem for p in (REPO_ROOT / "elements").glob("*.yaml")}
    for path, rule in _rules():
        for ref in rule["applies_to_elements"]:
            assert ref.removeprefix("pragmaticbim:element/") in elements, f"{path}: {ref}"


RF_ELEMENTS = (
    "architecture-wall-cladding-exterior",
    "architecture-wall-cladding-interior",
    "architecture-floor-covering",
    "architecture-ceiling-suspended",
    "architecture-wall-exterior",
    "architecture-wall-interior",
)
RF_KEY = "pbs:fire_property_reaction_to_fire"


def _element(slug: str) -> dict:
    return yaml.safe_load((REPO_ROOT / "elements" / f"{slug}.yaml").read_text(encoding="utf-8"))


def _attr(element: dict, name: str) -> dict:
    matches = [a for a in element["attributes"] if a["name"] == name]
    assert len(matches) == 1, name
    return matches[0]


def test_reaction_to_fire_value_list_has_rf1_to_rf4_in_four_languages() -> None:
    data = yaml.safe_load((REPO_ROOT / "values" / "reaction-to-fire.yaml").read_text(encoding="utf-8"))
    assert data["id"] == "pragmaticbim:value/reaction-to-fire"
    assert data["status"] == "active"
    for lang in LANGS:
        assert data["values"][lang] == ["RF1", "RF2", "RF3", "RF4"], lang
        assert str(data["name"].get(lang) or "").strip(), lang
        description = str(data["description"].get(lang) or "")
        assert "14-15" in description, lang
        assert "cr" in description, lang


def test_reaction_to_fire_attributes_resolve_on_lining_and_covering_elements() -> None:
    elements = {p.stem for p in (REPO_ROOT / "elements").glob("*.yaml")}
    for slug in RF_ELEMENTS:
        assert slug in elements, slug
        element = _element(slug)
        delivered = _attr(element, "ReactionToFire")
        required = _attr(element, "ReactionToFireRequired")
        for attribute in (delivered, required):
            assert attribute["allowed_values"] == "pragmaticbim:value/reaction-to-fire", slug
            assert attribute["datatype"] == "IfcLabel", slug
            for lang in LANGS:
                assert "RF1" in attribute["definition"][lang], f"{slug}: {lang}"
                assert "`cr`" in attribute["definition"][lang], f"{slug}: {lang}"
        assert "performance_property_key" not in delivered, slug
        assert required["performance_property_key"] == RF_KEY, slug
        assert required["requirement_kind"] == "performance", slug
        assert required["target_operator"] == "maximum", slug
        assert required["verified_by"] == {"name": "ReactionToFire", "pset": delivered["pset"]}, slug
        assert (REPO_ROOT / "values" / "reaction-to-fire.yaml").is_file()


def test_every_element_in_the_rules_that_hold_a_lining_layer_allows_rf() -> None:
    """The lining and covering elements named by the 14-15 rules carry the RF attribute."""
    named = {
        ref.removeprefix("pragmaticbim:element/")
        for _, rule in _rules()
        for ref in rule["applies_to_elements"]
    }
    for slug in (
        "architecture-wall-cladding-exterior",
        "architecture-wall-cladding-interior",
        "architecture-floor-covering",
        "architecture-ceiling-suspended",
    ):
        assert slug in named, slug
        assert slug in RF_ELEMENTS, slug
