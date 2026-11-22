"""Escape sign element, its value lists and the safety luminaire attributes (#123, VKF 17-15)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
SIGN_ID = "pragmaticbim:element/mep-escape-sign"
SAFETY_PSET = "ePset_SafetyLighting"
SAFETY_ATTRIBUTES = {
    "SafetyRatedDuration": ("IfcReal", "min"),
    "SafetyStartUpTime": ("IfcReal", "s"),
    "SafetySupplyType": ("IfcLabel", None),
    "SafetyFloorIlluminance": ("IfcReal", "lx"),
    "SafetyNotSwitchable": ("IfcBoolean", None),
}


def _load(folder: str, slug: str) -> dict[str, Any]:
    data = yaml.safe_load((REPO_ROOT / folder / f"{slug}.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict), slug
    return data


def _attribute(element: dict[str, Any], name: str) -> dict[str, Any]:
    return next(a for a in element["attributes"] if a["name"] == name)


def _all_ids(folder: str) -> set[str]:
    return {
        yaml.safe_load(p.read_text(encoding="utf-8"))["id"]
        for p in (REPO_ROOT / folder).glob("*.yaml")
    }


def _localized(value: Any, where: str) -> None:
    assert isinstance(value, dict), where
    for lang in LANGS:
        assert str(value.get(lang) or "").strip(), f"{where}.{lang}"


def test_escape_sign_element_is_active_and_localized() -> None:
    element = _load("elements", "mep-escape-sign")
    assert element["id"] == SIGN_ID
    assert element["code"] == "MEP-ESCAPE-SIGN"
    assert element["status"] == "active"
    _localized(element["name"], "name")
    _localized(element["definition"], "definition")
    _localized(element["applicability"], "applicability")
    assert {"pragmaticbim:domain/fire-protection", "pragmaticbim:domain/mep"} <= set(element["needed_in_domain"])
    for entity in ("entity_ifc2x3", "entity_ifc4", "entity_ifc4_3"):
        assert element[entity] == "IfcBuildingElementProxy"


def test_escape_sign_attributes_are_localized_and_resolve() -> None:
    element = _load("elements", "mep-escape-sign")
    values = _all_ids("values")
    workflows = _all_ids("workflows")
    names = [a["name"] for a in element["attributes"]]
    assert len(names) == len(set(names))
    orders = [a["sort_order"] for a in element["attributes"]]
    assert orders == sorted(set(orders))
    for attribute in element["attributes"]:
        _localized(attribute["definition"], attribute["name"])
        if attribute.get("allowed_values"):
            assert attribute["allowed_values"] in values, attribute["name"]
        for workflow in attribute["needed_for_workflows"]:
            assert workflow in workflows, attribute["name"]
    for name in ("LightingType", "SupplyType", "MountingHeight"):
        assert name in names


def test_escape_sign_lighting_type_covers_the_three_kinds() -> None:
    values = _load("values", "escape-sign-lighting-type")
    assert values["id"] == "pragmaticbim:value/escape-sign-lighting-type"
    _localized(values["name"], "name")
    _localized(values["description"], "description")
    for lang in LANGS:
        assert values["values"][lang] == ["ILLUMINATED", "BACKLIT", "AFTERGLOW"]
    attribute = _attribute(_load("elements", "mep-escape-sign"), "LightingType")
    assert attribute["allowed_values"] == values["id"]


def test_object_type_tokens_match_the_applicability_per_language() -> None:
    element = _load("elements", "mep-escape-sign")
    values = _load("values", "objecttype-escape-sign")
    assert _attribute(element, "ObjectType")["allowed_values"] == values["id"]
    for lang in LANGS:
        tokens = values["values"][lang]
        assert len(tokens) == 2
        for token in tokens:
            assert token in element["applicability"][lang], (lang, token)


def test_supply_type_is_shared_by_sign_and_luminaire() -> None:
    values = _load("values", "safety-lighting-supply-type")
    for lang in LANGS:
        assert values["values"][lang] == ["SINGLE_BATTERY", "CENTRAL_BATTERY", "GENERATOR"]
    sign = _load("elements", "mep-escape-sign")
    fixture = _load("elements", "mep-light-fixture")
    assert _attribute(sign, "SupplyType")["allowed_values"] == values["id"]
    assert _attribute(fixture, "SafetySupplyType")["allowed_values"] == values["id"]


def test_light_fixture_carries_safety_lighting_attributes() -> None:
    fixture = _load("elements", "mep-light-fixture")
    names = [a["name"] for a in fixture["attributes"]]
    assert len(names) == len(set(names))
    for name, (datatype, unit) in SAFETY_ATTRIBUTES.items():
        attribute = _attribute(fixture, name)
        assert attribute["pset"] == SAFETY_PSET, name
        assert attribute["datatype"] == datatype, name
        assert attribute.get("unit") == unit, name
        assert attribute["status"] == "active", name
        _localized(attribute["definition"], name)
    assert "SECURITYLIGHTING" in _all_tokens("predefinedtype-light-fixture")


def test_safety_attributes_wait_for_contract_keys() -> None:
    """No contract key exists for safety lighting yet; do not invent one."""
    fixture = _load("elements", "mep-light-fixture")
    for name in SAFETY_ATTRIBUTES:
        assert not _attribute(fixture, name).get("performance_property_key"), name


def test_existing_light_fixture_attributes_are_unchanged() -> None:
    fixture = _load("elements", "mep-light-fixture")
    assert fixture["code"] == "MEP-LIGHT"
    assert [a["name"] for a in fixture["attributes"]][:5] == [
        "PredefinedType",
        "Tag",
        "Status",
        "WarrantyEndDate",
        "DatasheetLink",
    ]


SHACL_RULES = {
    "vkf-17-15-009-sicherheitsbeleuchtung-dauer-schaltung.yaml",
    "vkf-17-15-010-sicherheitsleuchten-anordnung.yaml",
    "vkf-17-15-011-sicherheitsbeleuchtung-beleuchtungsstaerke.yaml",
}


def test_vkf_17_15_checkable_rules_are_shacl_defined() -> None:
    """Rules 009–011 are SHACL; the rest stay text-only until more contract facts exist."""
    for path in sorted((REPO_ROOT / "rules").glob("vkf-17-15-*.yaml")):
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        expected = "shacl_defined" if path.name in SHACL_RULES else "reviewed"
        assert rule["rule_status"] == expected, path.name


def _all_tokens(slug: str) -> list[str]:
    return _load("values", slug)["values"]["en"]
