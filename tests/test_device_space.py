"""Geräteplatz: element, value lists, catalogue vignette and components."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from catalog.mapping import map_device_space_params
from catalog.sample_data import SAMPLE_CATALOG
from generators.device_space import generate_device_space

ROOT = Path(__file__).resolve().parents[1]
ELEMENT_ID = "pragmaticbim:element/architecture-device-space"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_element_is_localized_and_listed_in_the_architecture_model() -> None:
    element = _load("elements/architecture-device-space.yaml")
    assert element["id"] == ELEMENT_ID
    assert element["entity_ifc4"] == "IfcBuildingElementProxy"
    for field in ("name", "definition", "applicability"):
        assert all(str(element[field].get(lang) or "").strip() for lang in LANGS), field
    object_types = _load("values/objecttype-device-space.yaml")["values"]
    for lang in LANGS:
        expression = element["applicability"][lang].replace('"', "")
        assert expression.count(f"ObjectType={object_types[lang][0]})") == 2, lang
    for name in ("picture_link", "attachment_link", "picture_print_link"):
        assert list(ROOT.glob(f"media/**/{element[name]}")), name
    assert ELEMENT_ID in _load("models/architecture.yaml")["included_elements"]


def test_name_value_list_has_the_same_length_in_every_language() -> None:
    values = _load("values/name-device-space.yaml")["values"]
    lengths = {len(values[lang]) for lang in LANGS}
    assert len(lengths) == 1
    assert "Operationstisch" in values["de"]


def test_vignette_places_device_spaces_inside_the_room() -> None:
    entry = next(item for item in SAMPLE_CATALOG if item["id"] == "device-space-01")
    ifc_file, spaces = generate_device_space(map_device_space_params(entry))
    names = [proxy.Name for proxy in spaces]
    assert names == ["Operationstisch", "Medizingerät"]
    allowed = set(_load("values/name-device-space.yaml")["values"]["de"])
    for proxy in spaces:
        assert proxy.is_a("IfcBuildingElementProxy")
        assert proxy.ObjectType == "Geräteplatz"
        assert proxy.PredefinedType == "USERDEFINED"
        assert proxy.Name in allowed


def test_plant_and_device_components_are_ordered_by_their_rooms() -> None:
    used: set[str] = set()
    for path in (ROOT / "room_types").glob("*.yaml"):
        for configuration in _load(f"room_types/{path.name}")["configurations"]:
            for item in configuration.get("equipment") or []:
                used.update(item["components"])
    for path in (ROOT / "components").glob("*.yaml"):
        component = _load(f"components/{path.name}")
        if component["category"] in {"device", "plant"}:
            assert component["id"] in used, f"{component['id']} is not ordered by any room type"
