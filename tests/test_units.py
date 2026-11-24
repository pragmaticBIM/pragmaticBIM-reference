"""Container room types and their gross-volume presets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
GROSS = "pragmaticbim:element/spaces-gross-volume"
OBJECT_TYPE = {
    "de": "Bruttovolumen",
    "fr": "Volume brut",
    "it": "Volume lordo",
    "en": "Gross volume",
}
DWELLING_SIZES = {
    "pragmaticbim:room-type/wohnung-1-5": 45,
    "pragmaticbim:room-type/wohnung-2-5": 65,
    "pragmaticbim:room-type/wohnung-3-5": 90,
    "pragmaticbim:room-type/wohnung-4-5": 115,
    "pragmaticbim:room-type/wohnung-5-5": 135,
}
OFFICE_SIZES = {
    "pragmaticbim:room-type/bueroeinheit-klein": 150,
    "pragmaticbim:room-type/bueroeinheit-mittel": 400,
    "pragmaticbim:room-type/bueroeinheit-gross": 1000,
}
SHOP_SIZES = {
    "pragmaticbim:room-type/ladenlokal-klein": 80,
    "pragmaticbim:room-type/ladenlokal-mittel": 250,
    "pragmaticbim:room-type/ladenlokal-gross": 800,
}
# Size variants with a planned area, keyed by the base container they extend.
SIZES_BY_PARENT = {
    "pragmaticbim:room-type/wohnung": DWELLING_SIZES,
    "pragmaticbim:room-type/bueroeinheit": OFFICE_SIZES,
    "pragmaticbim:room-type/ladenlokal": SHOP_SIZES,
}
# Variants without a planned area, keyed by the base container they extend.
VARIANTS_BY_PARENT = {
    "pragmaticbim:room-type/hoteleinheit": {
        "pragmaticbim:room-type/hotel-einzelzimmer",
        "pragmaticbim:room-type/hotel-doppelzimmer",
        "pragmaticbim:room-type/hotel-suite",
    },
}
SIZED_IDS = {room_id for sizes in SIZES_BY_PARENT.values() for room_id in sizes}
# Containers added after the unit-type migration carry no legacy unit-type id.
NEW_CONTAINER_IDS = {
    "pragmaticbim:room-type/hoteleinheit",
    *OFFICE_SIZES,
    *SHOP_SIZES,
}
CONTAINER_IDS = {
    *SIZES_BY_PARENT,
    *SIZED_IDS,
    *VARIANTS_BY_PARENT,
    *(room_id for variants in VARIANTS_BY_PARENT.values() for room_id in variants),
    "pragmaticbim:room-type/keller",
    "pragmaticbim:room-type/vertikale-erschliessung",
    "pragmaticbim:room-type/horizontale-erschliessung",
    "pragmaticbim:room-type/parkgarage",
}


def _load_dir(folder: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / folder).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        data["_path"] = path
        items.append(data)
    return items


def _localized(item: dict[str, Any], field: str) -> None:
    value = item.get(field)
    assert isinstance(value, dict), f"{item.get('_path') or item.get('id')}: missing {field}"
    for lang in LANGS:
        assert str(value.get(lang) or "").strip(), f"{item.get('id')}: missing {field}.{lang}"


def _presets(container: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    configurations = container.get("configurations") or []
    assert len(configurations) == 1, container["id"]
    for preset in configurations[0].get("attribute_presets") or []:
        assert preset.get("element") == GROSS, container["id"]
        assert preset["name"] not in found, f"{container['id']}: duplicate {preset['name']}"
        found[preset["name"]] = preset.get("value")
    return found


def test_container_room_types() -> None:
    room_types = _load_dir("room_types")
    by_id = {item["id"]: item for item in room_types}
    containers = [item for item in room_types if item.get("room_type_kind") == "container"]
    assert {item["id"] for item in containers} == CONTAINER_IDS

    for container in containers:
        _localized(container, "name")
        _localized(container, "definition")
        aliases = container.get("legacy_ids") or []
        if container["id"] in NEW_CONTAINER_IDS:
            assert not aliases, container["id"]
        else:
            assert len(aliases) == 1 and aliases[0].startswith("pragmaticbim:unit-type/"), container["id"]
        components = container.get("contains") or []
        assert components, f"{container['id']}: missing contains"
        component_ids = [item["room_type"] for item in components]
        assert len(component_ids) == len(set(component_ids)), container["id"]
        assert not (set(component_ids) - set(by_id)), container["id"]
        presets = _presets(container)
        expected = {"PredefinedType", "ObjectType", "LongName"}
        if container["id"] in SIZED_IDS:
            expected.add("GrossPlannedArea")
        assert set(presets) == expected, container["id"]
        assert "restrictions" not in container["configurations"][0], container["id"]
        assert presets["PredefinedType"] == "GFA", container["id"]
        assert presets["ObjectType"] == OBJECT_TYPE, container["id"]
        assert presets["LongName"] == container["name"], container["id"]

    for parent_id, sizes in SIZES_BY_PARENT.items():
        assert "extends" not in by_id[parent_id], parent_id
        for room_id, area in sizes.items():
            container = by_id[room_id]
            assert container["extends"] == parent_id, room_id
            assert container["uses"] == by_id[parent_id]["uses"], room_id
            assert _presets(container)["GrossPlannedArea"] == area, room_id

    for parent_id, variants in VARIANTS_BY_PARENT.items():
        assert "extends" not in by_id[parent_id], parent_id
        for room_id in variants:
            assert by_id[room_id]["extends"] == parent_id, room_id
            assert by_id[room_id]["uses"] == by_id[parent_id]["uses"], room_id
