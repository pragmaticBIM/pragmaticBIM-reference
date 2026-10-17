"""Guard the chain goal level → target attribute → delivered attribute → contract key."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ENUMS = (
    ROOT.parents[1] / "pragmatic-bim-data-contract" / "contract" / "entity_schema_enums.yaml"
)
KEY_ENUMS = (
    "FirePropertyKey",
    "AcousticPropertyKey",
    "ThermalPropertyKey",
    "StructuralPropertyKey",
    "IndoorEnvironmentPropertyKey",
    "EnvironmentalPropertyKey",
    "SecurityPropertyKey",
    "MaterialPropertyKey",
)
# Pinned copy of the contract key meanings used by the catalogue, for checkouts
# without the sibling data-contract repository.
PINNED_KEYS = {
    "pbs:fire_property_resistance_rating",
    "pbs:thermal_property_u_value",
    "pbs:acoustic_property_airborne_sound_rating_db",
    "pbs:acoustic_property_impact_sound_rating_db",
    "pbs:structural_property_seismic_structure_class",
    "pbs:structural_property_design_area_load",
    "pbs:structural_property_design_point_load",
    "pbs:structural_property_vibration_class",
    "pbs:environmental_property_gwp_embodied",
    "pbs:indoor_environment_winter_temperature_min",
    "pbs:indoor_environment_winter_temperature_max",
    "pbs:indoor_environment_summer_temperature_min",
    "pbs:indoor_environment_summer_temperature_max",
    "pbs:indoor_environment_relative_humidity_min",
    "pbs:indoor_environment_relative_humidity_max",
    "pbs:indoor_environment_outdoor_air_flow_rate",
    "pbs:indoor_environment_peak_occupancy",
    "pbs:indoor_environment_daily_operating_hours",
    "pbs:indoor_environment_required_illuminance",
}
OPERATORS = {"equals", "minimum", "maximum", "range"}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def _elements() -> dict[str, dict[str, Any]]:
    elements = {}
    for path in sorted((ROOT / "elements").glob("*.yaml")):
        data = _load(path)
        elements[data["id"]] = data
    return elements


def _attribute(element: dict[str, Any], name: str, pset: str | None) -> dict[str, Any] | None:
    for attribute in element.get("attributes") or []:
        if attribute.get("name") == name and attribute.get("pset") == pset:
            return attribute
    return None


def _contract_keys() -> set[str]:
    if not CONTRACT_ENUMS.is_file():
        return PINNED_KEYS
    enums = _load(CONTRACT_ENUMS)["enums"]
    return {
        entry["meaning"]
        for enum_name in KEY_ENUMS
        for entry in (enums[enum_name]["permissible_values"] or {}).values()
    }


def _linked_attributes() -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    return [
        (element_id, element, attribute)
        for element_id, element in _elements().items()
        for attribute in element.get("attributes") or []
        if attribute.get("performance_property_key")
    ]


def _goal_targets() -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    found = []
    for path in sorted((ROOT / "project_goals").glob("*.yaml")):
        for level in _load(path).get("levels") or []:
            for target in level.get("performance_targets") or []:
                found.append((level["code"], level, target))
    return found


def test_pinned_keys_match_the_contract() -> None:
    if not CONTRACT_ENUMS.is_file():
        pytest.skip("data-contract repository not checked out next to this one")
    assert PINNED_KEYS <= _contract_keys()


def test_linked_attributes_name_a_contract_key_and_a_delivered_value() -> None:
    keys = _contract_keys()
    linked = _linked_attributes()
    assert linked
    for element_id, element, attribute in linked:
        label = f"{element_id} {attribute['name']}"
        assert attribute["performance_property_key"] in keys, label
        assert attribute.get("requirement_kind") == "performance", label
        assert attribute.get("target_operator") in OPERATORS, label
        verified_by = attribute.get("verified_by")
        assert isinstance(verified_by, dict), label
        delivered = _attribute(element, verified_by["name"], verified_by.get("pset"))
        assert delivered is not None, f"{label}: verified_by not on element"
        assert delivered is not attribute, label
        assert not delivered.get("performance_property_key"), label
        assert delivered.get("unit") == attribute.get("unit"), label
        assert delivered.get("datatype") == attribute.get("datatype"), label


def test_goal_targets_resolve_to_performance_attributes() -> None:
    elements = _elements()
    targets = _goal_targets()
    assert targets
    for code, _, target in targets:
        label = f"{code} {target['name']}"
        element = elements.get(target["element"])
        assert element is not None, label
        attribute = _attribute(element, target["name"], target.get("pset"))
        assert attribute is not None, label
        assert attribute.get("requirement_kind") == "performance", label


def test_goal_target_values_fit_the_attribute() -> None:
    elements = _elements()
    for code, _, target in _goal_targets():
        if "value" not in target:
            continue
        attribute = _attribute(
            elements[target["element"]], target["name"], target.get("pset")
        )
        value = target["value"]
        label = f"{code} {target['name']}"
        if attribute["datatype"] == "IfcBoolean":
            assert isinstance(value, bool), label
        elif attribute["datatype"] in ("IfcLabel", "IfcText", "IfcIdentifier"):
            assert isinstance(value, str), label
            if attribute.get("allowed_values"):
                slug = attribute["allowed_values"].rsplit("/", 1)[-1]
                allowed = _load(ROOT / "values" / f"{slug}.yaml")["values"]["de"]
                assert value in allowed, label
        else:
            assert isinstance(value, (int, float)) and not isinstance(value, bool), label
            assert value > 0, label


def test_levels_tighten_numeric_targets_upwards() -> None:
    """A higher level of the same goal never relaxes a numeric default."""
    elements = _elements()
    for path in sorted((ROOT / "project_goals").glob("*.yaml")):
        previous: dict[tuple[str, str], float] = {}
        levels = sorted(_load(path).get("levels") or [], key=lambda level: level["sort_order"])
        for level in levels:
            for target in level.get("performance_targets") or []:
                value = target.get("value")
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue
                attribute = _attribute(
                    elements[target["element"]], target["name"], target.get("pset")
                )
                key = (target["element"], target["name"])
                operator = attribute.get("target_operator")
                if key in previous and operator == "minimum":
                    assert value >= previous[key], (path.name, level["code"], key)
                if key in previous and operator == "maximum":
                    assert value <= previous[key], (path.name, level["code"], key)
                previous[key] = value
