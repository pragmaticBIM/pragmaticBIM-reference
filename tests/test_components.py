"""Components and the equipment and openings that room types order with them."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CLEARANCE_NAMES = "pragmaticbim:value/name-movement-clearance"
OPENING_HOSTS = {"wall_opening"}
OPENING_CATEGORIES = {"door", "window", "passage"}


def _load_dir(folder: str) -> list[dict[str, Any]]:
    items = []
    for path in sorted((REPO_ROOT / folder).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        data["_path"] = path
        items.append(data)
    return items


@lru_cache(maxsize=1)
def _components() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in _load_dir("components")}


@lru_cache(maxsize=1)
def _elements() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in _load_dir("elements")}


@lru_cache(maxsize=1)
def _values() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in _load_dir("values")}


@lru_cache(maxsize=1)
def _room_types() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in _load_dir("room_types")}


@lru_cache(maxsize=1)
def _goal_levels() -> set[str]:
    return {
        level["id"]
        for goal in _load_dir("project_goals")
        for level in goal.get("levels") or []
    }


@lru_cache(maxsize=1)
def _scenario_options() -> set[str]:
    return {
        option["id"]
        for scenario in _load_dir("usage_scenarios")
        for option in scenario.get("options") or []
    }


def _tokens(value_id: str, lang: str) -> list[str]:
    return [str(t) for t in (_values()[value_id].get("values") or {}).get(lang) or []]


def _attribute(element: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((a for a in element.get("attributes") or [] if a["name"] == name and not a.get("pset")), None)


def _localized(value: Any, where: str) -> None:
    assert isinstance(value, dict), f"{where}: expected de/fr/it/en"
    assert set(value) == set(LANGS), f"{where}: expected {LANGS}, got {sorted(value)}"
    for lang in LANGS:
        assert str(value[lang]).strip(), f"{where}.{lang} is empty"


def _check_condition(condition: dict[str, Any] | None, where: str) -> None:
    if condition is None:
        return
    assert condition, f"{where}: empty condition"
    assert set(condition) <= {"project_goal_levels", "scenario_options"}, where
    unknown = set(condition.get("project_goal_levels") or []) - _goal_levels()
    assert not unknown, f"{where}: unknown project goal levels {sorted(unknown)}"
    unknown = set(condition.get("scenario_options") or []) - _scenario_options()
    assert not unknown, f"{where}: unknown scenario options {sorted(unknown)}"


def _component_ids() -> list[str]:
    return [path.stem for path in sorted((REPO_ROOT / "components").glob("*.yaml"))]


# ── Components ───────────────────────────────────────────────────────────────


def test_component_ids_and_codes_are_unique() -> None:
    components = list(_components().values())
    assert components, "components/ is empty"
    codes = [item["code"] for item in components]
    assert len(codes) == len(set(codes)), "duplicate component codes"
    orders = [item["sort_order"] for item in components]
    assert len(orders) == len(set(orders)), "duplicate component sort_order"


@pytest.mark.parametrize("slug", _component_ids())
def test_component(slug: str) -> None:
    item = _components()[f"pragmaticbim:component/{slug}"]
    where = item["_path"].name
    assert SLUG.match(slug), where
    _localized(item.get("name"), f"{where} name")
    _localized(item.get("definition"), f"{where} definition")
    assert item.get("status") in {"active", "deprecated"}, where

    element = _elements().get(item.get("element"))
    assert element, f"{where}: unknown element {item.get('element')}"

    predefined = _attribute(element, "PredefinedType")
    if item.get("predefined_type") is not None:
        assert predefined and predefined.get("allowed_values"), f"{where}: element has no PredefinedType list"
        allowed = set(_tokens(predefined["allowed_values"], "en"))
        assert item["predefined_type"] in allowed, f"{where}: {item['predefined_type']} not in {sorted(allowed)}"

    applicability = element.get("applicability")
    needs_object_type = "ObjectType=" in json.dumps(applicability, ensure_ascii=False)
    object_type = _attribute(element, "ObjectType")
    if needs_object_type:
        assert "object_type" in item, f"{where}: element filters on ObjectType"
    if "object_type" in item:
        _localized(item["object_type"], f"{where} object_type")
        assert object_type and object_type.get("allowed_values"), f"{where}: element has no ObjectType list"
        for lang in LANGS:
            assert item["object_type"][lang] in _tokens(object_type["allowed_values"], lang), (
                f"{where}: object_type.{lang}={item['object_type'][lang]!r} not in value list"
            )

    if "ifc_name" in item:
        name = _attribute(element, "Name")
        assert name and name.get("allowed_values"), f"{where}: element has no Name list"
        for lang in LANGS:
            assert item["ifc_name"][lang] in _tokens(name["allowed_values"], lang), f"{where}: ifc_name.{lang}"

    params = item.get("parameters") or {}
    assert params, f"{where}: no parameters"
    for key, spec in params.items():
        assert re.match(r"^[a-z][a-z0-9_]*$", key), f"{where}: parameter {key}"
        lo, hi = spec.get("min", spec["default"]), spec.get("max", spec["default"])
        assert lo <= spec["default"] <= hi, f"{where}: {key} default outside min/max"

    placement = item["placement"]
    host = placement["host"]
    is_opening = item["category"] in OPENING_CATEGORIES
    assert (host in OPENING_HOSTS) == is_opening, f"{where}: host {host} does not fit category {item['category']}"
    if host in {"wall_face", "wall_corner", "wall_opening"}:
        assert placement.get("edge_kinds"), f"{where}: wall-hosted component needs edge_kinds"
    if isinstance(placement.get("elevation"), str):
        assert placement["elevation"] in params, f"{where}: elevation parameter missing"

    for index, clearance in enumerate(item.get("clearances") or []):
        cwhere = f"{where} clearance {index}"
        _localized(clearance.get("name"), cwhere)
        for lang in LANGS:
            assert clearance["name"][lang] in _tokens(CLEARANCE_NAMES, lang), f"{cwhere}: name.{lang}"
        for dim in ("width", "depth"):
            value = clearance[dim]
            if isinstance(value, str):
                assert value in params, f"{cwhere}: {dim} refers to unknown parameter {value}"
            else:
                assert value > 0, f"{cwhere}: {dim} must be positive"
        if clearance["side"] == "swing":
            assert is_opening, f"{cwhere}: only openings swing"
        _check_condition(clearance.get("when"), cwhere)


def test_component_parts_resolve_without_cycles() -> None:
    components = _components()

    def walk(component_id: str, seen: tuple[str, ...]) -> None:
        assert component_id not in seen, f"part cycle: {' -> '.join(seen + (component_id,))}"
        for part in components[component_id].get("parts") or []:
            assert part["component"] in components, f"{component_id}: unknown part {part['component']}"
            assert components[part["component"]]["category"] not in OPENING_CATEGORIES
            walk(part["component"], seen + (component_id,))

    for component_id, item in components.items():
        if item.get("parts"):
            assert item["representation"]["body"] == "parts", component_id
        walk(component_id, ())


# ── Room type equipment and openings ─────────────────────────────────────────


def _configurations() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (room_type, configuration)
        for room_type in _room_types().values()
        for configuration in room_type.get("configurations") or []
    ]


def _quantity(value: Any, where: str) -> None:
    if isinstance(value, int):
        assert value >= 1, where
        return
    assert isinstance(value, dict) and "min" in value, f"{where}: quantity"
    if "per" in value:
        assert value["per"]["quantity"] in {"net_floor_area", "peak_occupancy"}, f"{where}: per.quantity"
        assert value["per"]["divisor"] > 0, f"{where}: per.divisor"
        assert "default" not in value, f"{where}: per computes the count; drop default"
    lo = value["min"]
    hi = value.get("max", max(lo, value.get("default", lo)))
    assert 0 <= lo <= hi, f"{where}: quantity min/max"
    if "default" in value:
        assert lo <= value["default"] <= hi, f"{where}: quantity default"


def _params(params: dict[str, Any] | None, component_ids: list[str], where: str) -> None:
    for key, spec in (params or {}).items():
        for component_id in component_ids:
            assert key in _components()[component_id]["parameters"], f"{where}: {component_id} has no {key}"
            base = _components()[component_id]["parameters"][key]
            for bound in ("default", "min", "max"):
                if bound in spec:
                    lo = base.get("min", base["default"])
                    hi = base.get("max", base["default"])
                    assert lo <= spec[bound] <= hi, (
                        f"{where}: {key}.{bound}={spec[bound]} outside {component_id} range {lo}–{hi}"
                    )
        lo, hi = spec.get("min"), spec.get("max")
        if lo is not None and hi is not None:
            assert lo <= hi, f"{where}: {key} min > max"
        if "default" in spec:
            assert (lo is None or lo <= spec["default"]) and (hi is None or spec["default"] <= hi), (
                f"{where}: {key} default outside min/max"
            )


def _items(configuration: dict[str, Any], key: str, prefix: str) -> list[dict[str, Any]]:
    items = configuration.get(key) or []
    cfg_slug = configuration["id"].split("/")[-1]
    for order, item in enumerate(items, start=1):
        assert item["id"].startswith(f"pragmaticbim:room-type-{prefix}/{cfg_slug}-"), item["id"]
        assert item["sort_order"] == order, f"{item['id']}: sort_order"
        assert item["status"] in {"active", "deprecated"}, item["id"]
        assert item["components"], item["id"]
        assert len(item["components"]) == len(set(item["components"])), item["id"]
        unknown = set(item["components"]) - set(_components())
        assert not unknown, f"{item['id']}: unknown components {sorted(unknown)}"
        _quantity(item["quantity"], item["id"])
        _params(item.get("params"), item["components"], item["id"])
        _check_condition(item.get("when"), item["id"])
        _check_condition(item.get("unless"), item["id"])
    return items


def test_equipment_and_opening_ids_are_unique() -> None:
    ids = [
        item["id"]
        for _, configuration in _configurations()
        for key in ("equipment", "openings")
        for item in configuration.get(key) or []
    ]
    assert ids, "no room type orders equipment or openings"
    assert len(ids) == len(set(ids))


def test_room_type_equipment() -> None:
    for room_type, configuration in _configurations():
        for item in _items(configuration, "equipment", "equipment"):
            for component_id in item["components"]:
                category = _components()[component_id]["category"]
                assert category not in OPENING_CATEGORIES, f"{item['id']}: {component_id} is an opening"
        assert room_type.get("room_type_kind") != "container" or not configuration.get("equipment"), (
            f"{room_type['id']}: containers hold rooms, not equipment"
        )


def test_room_type_openings() -> None:
    room_types = _room_types()
    for room_type, configuration in _configurations():
        for item in _items(configuration, "openings", "opening"):
            for component_id in item["components"]:
                category = _components()[component_id]["category"]
                assert category in OPENING_CATEGORIES, f"{item['id']}: {component_id} is not an opening"
            target = item["connects_to"]
            assert len(target) == 1, f"{item['id']}: connects_to takes one mode"
            if "room_types" in target:
                unknown = set(target["room_types"]) - set(room_types)
                assert not unknown, f"{item['id']}: unknown room types {sorted(unknown)}"
            elif "exterior" in target:
                assert target["exterior"] is True, item["id"]
                for component_id in item["components"]:
                    kinds = _components()[component_id]["placement"]["edge_kinds"]
                    assert "exterior" in kinds, f"{item['id']}: {component_id} cannot sit in an exterior wall"
            else:
                assert target == {"relationships": "incoming"}, item["id"]
            if item["function"] == "daylight":
                assert "exterior" in target, f"{item['id']}: daylight comes from outside"
            if "fallback" in item:
                assert isinstance(item["quantity"], dict) and item["quantity"]["min"] == 0, (
                    f"{item['id']}: a fallback only makes sense when the opening is optional"
                )
            if "glazing_to_floor_ratio_min" in item:
                assert item["function"] == "daylight", item["id"]


def test_incoming_openings_have_relationships() -> None:
    """``relationships: incoming`` needs at least one scenario edge into the room type."""
    incoming: set[str] = set()
    for scenario in _load_dir("usage_scenarios"):
        for option in scenario.get("options") or []:
            for relationship in option.get("room_relationships") or []:
                incoming.add(relationship["to_room_type"])
    for room_type, configuration in _configurations():
        for item in configuration.get("openings") or []:
            if item["connects_to"] == {"relationships": "incoming"}:
                assert room_type["id"] in incoming, f"{item['id']}: no scenario leads into {room_type['id']}"


# ── JSON Schema ──────────────────────────────────────────────────────────────


def _schema_validator(name: str):
    jsonschema = pytest.importorskip("jsonschema")
    referencing = pytest.importorskip("referencing")
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in (REPO_ROOT / "schema").glob("*.schema.json")
    }
    registry = referencing.Registry().with_resources(
        (schema["$id"], referencing.Resource.from_contents(schema)) for schema in schemas.values()
    )
    schema = schemas[name]
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema, registry=registry)


def _clean(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_")}


def test_components_match_json_schema() -> None:
    validator = _schema_validator("component.schema.json")
    for item in _components().values():
        errors = sorted(validator.iter_errors(_clean(item)), key=lambda e: list(e.path))
        assert not errors, f"{item['_path'].name}: {errors[0].message} at {list(errors[0].path)}"


def test_room_type_extensions_match_json_schema() -> None:
    validator = _schema_validator("room-type-equipment.schema.json")
    for _, configuration in _configurations():
        extension = {key: configuration[key] for key in ("equipment", "openings") if key in configuration}
        errors = sorted(validator.iter_errors(extension), key=lambda e: list(e.path))
        assert not errors, f"{configuration['id']}: {errors[0].message} at {list(errors[0].path)}"
