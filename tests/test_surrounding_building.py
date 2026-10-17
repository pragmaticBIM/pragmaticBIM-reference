"""Guard surrounding neighbour building volumes for stakeholder dialogue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from ifcopenshell.util.element import get_psets

from catalog.mapping import map_surrounding_building_params
from catalog.sample_data import SAMPLE_CATALOG
from generators.surrounding_building import (
    generate_surrounding_building,
    neighbor_gross_volume,
)


ROOT = Path(__file__).resolve().parents[1]
ELEMENT_ID = "pragmaticbim:element/architecture-surrounding-building"
WORKFLOW_ID = "pragmaticbim:workflow/qas-stakeholder-dialog"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_surrounding_building_element_is_localized_and_linked() -> None:
    element = _load("elements/architecture-surrounding-building.yaml")
    attributes = {attribute["name"]: attribute for attribute in element["attributes"]}

    assert element["id"] == ELEMENT_ID
    assert element["code"] == "ARC-UMG-NEIGHBOR"
    assert element["entity_ifc4"] == "IfcBuildingElementProxy"
    assert element["status"] == "active"
    for field in ("name", "definition"):
        assert all(str(element[field].get(lang) or "").strip() for lang in LANGS)

    assert {
        "Name",
        "PredefinedType",
        "ObjectType",
        "EinspracheRisiko",
    } <= attributes.keys()
    assert attributes["ObjectType"]["is_applicability"] is True
    assert attributes["ObjectType"]["allowed_values"] == (
        "pragmaticbim:value/objecttype-surrounding-building"
    )
    assert attributes["EinspracheRisiko"]["pset"] == "Pset_UmgebungCommon"
    assert attributes["EinspracheRisiko"]["allowed_values"] == (
        "pragmaticbim:value/objection-risk"
    )
    for attribute in attributes.values():
        assert WORKFLOW_ID in attribute["needed_for_workflows"]


def test_surrounding_building_is_in_umg_and_value_lists_exist() -> None:
    model = _load("models/surroundings.yaml")
    assert ELEMENT_ID in model["included_elements"]
    assert "pragmaticbim:element/landscape-tree" in model["included_elements"]
    assert "Volumen, Höhe, Lage" in model["definition"]["de"]
    assert "Was führen" not in model["definition"]["de"]
    assert "Was übertrieben ist" not in model["definition"]["de"]

    object_type = _load("values/objecttype-surrounding-building.yaml")
    assert "Umgebungsbau" in object_type["values"]["de"]
    risk = _load("values/objection-risk.yaml")
    assert risk["values"]["de"] == ["HOCH", "MITTEL", "TIEF"]


def test_surrounding_building_generator_creates_three_gross_volumes() -> None:
    entry = next(item for item in SAMPLE_CATALOG if item["id"] == "surrounding-building-01")
    ifc_file, proxies = generate_surrounding_building(
        map_surrounding_building_params(entry)
    )

    assert len(proxies) == 3
    names = [proxy.Name for proxy in proxies]
    assert names == ["N001", "N002", "N003"]
    for proxy in proxies:
        assert proxy.is_a("IfcBuildingElementProxy")
        assert proxy.ObjectType == "Umgebungsbau"
        assert proxy.PredefinedType == "USERDEFINED"

    risks = [
        get_psets(proxy)["Pset_UmgebungCommon"]["EinspracheRisiko"] for proxy in proxies
    ]
    assert risks == ["HOCH", "MITTEL", "TIEF"]
    assert len(ifc_file.by_type("IfcSlab")) >= 1

    rep_types = [
        proxy.Representation.Representations[0].RepresentationType for proxy in proxies
    ]
    assert rep_types == ["SweptSolid", "Brep", "Brep"]
    volumes = [
        get_psets(proxy)["Qto_BuildingElementProxyBaseQuantities"]["GrossVolume"]
        for proxy in proxies
    ]
    assert volumes == [
        round(neighbor_gross_volume(10.0, 7.0, 12.0), 3),
        round(neighbor_gross_volume(8.0, 6.0, 8.0, "GABLE"), 3),
        round(neighbor_gross_volume(7.0, 5.5, 6.0, "GABLE"), 3),
    ]
    assert volumes[1] < 8.0 * 6.0 * 8.0
    assert volumes[2] < 7.0 * 5.5 * 6.0
