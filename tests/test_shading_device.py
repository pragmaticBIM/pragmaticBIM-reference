"""Guard IfcShadingDevice element, window SunProtection, and catalog geometry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from catalog.mapping import map_shading_device_params
from catalog.sample_data import SAMPLE_CATALOG
from generators.shading import generate_shading


ROOT = Path(__file__).resolve().parents[1]
ELEMENT_ID = "pragmaticbim:element/architecture-shading-device"
BPS_WORKFLOW = "pragmaticbim:workflow/des-abstractbim-building-performance-simulation"
FACADE_WORKFLOW = "pragmaticbim:workflow/des-facade-planning"
TENDER_WORKFLOW = "pragmaticbim:workflow/bes-window-tender-basis"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_shading_device_element_is_localized_and_linked() -> None:
    element = _load("elements/architecture-shading-device.yaml")
    attributes = {attribute["name"]: attribute for attribute in element["attributes"]}

    assert element["id"] == ELEMENT_ID
    assert element["code"] == "ARC-SHADING"
    assert element["entity_ifc4"] == "IfcShadingDevice"
    assert element["entity_ifc2x3"] == "IfcBuildingElementProxy"
    assert attributes["PredefinedType"]["ifc_versions"] == ["ifc4", "ifc4x3"]
    assert attributes["ObjectType"]["ifc_versions"] == ["ifc2x3"]
    assert attributes["ObjectType"]["allowed_values"] == (
        "pragmaticbim:value/objecttype-shading-device"
    )
    assert "ifc2x3" not in attributes["IsExternal"]["ifc_versions"]
    assert element["status"] == "active"
    for field in ("name", "definition"):
        assert all(str(element[field].get(lang) or "").strip() for lang in LANGS)

    assert {"Name", "PredefinedType", "IsExternal", "eBKP"} <= attributes.keys()
    assert attributes["PredefinedType"]["allowed_values"] == (
        "pragmaticbim:value/predefinedtype-shading-device"
    )
    assert attributes["eBKP"]["allowed_values"] == "pragmaticbim:value/ebkp-h-shading"
    assert attributes["IsExternal"]["pset"] == "Pset_ShadingDeviceCommon"
    for attribute in attributes.values():
        assert BPS_WORKFLOW in attribute["needed_for_workflows"]
        assert FACADE_WORKFLOW in attribute["needed_for_workflows"]


def test_shading_device_value_lists_exist() -> None:
    predefined = _load("values/predefinedtype-shading-device.yaml")
    assert predefined["values"]["de"] == [
        "JALOUSIE",
        "SHUTTER",
        "AWNING",
        "USERDEFINED",
        "NOTDEFINED",
    ]
    ebkp = _load("values/ebkp-h-shading.yaml")
    assert ebkp["values"]["de"] == ["E03.04"]
    object_type = _load("values/objecttype-shading-device.yaml")
    assert object_type["values"]["de"] == ["Sonnenschutz"]
    assert object_type["values"]["en"] == ["Shading device"]
    sun = _load("values/sun-protection.yaml")
    assert sun["values"]["de"] == [
        "NONE",
        "JALOUSIE",
        "SHUTTER",
        "AWNING",
        "USERDEFINED",
    ]


def test_shading_device_is_in_facade_and_architecture_models() -> None:
    facade = _load("models/facade.yaml")
    architecture = _load("models/architecture.yaml")
    assert ELEMENT_ID in facade["included_elements"]
    assert ELEMENT_ID in architecture["included_elements"]


def test_exterior_window_has_sun_protection_for_simulation_and_tender() -> None:
    exterior = _load("elements/architecture-window-exterior.yaml")
    attributes = {attribute["name"]: attribute for attribute in exterior["attributes"]}
    sun = attributes["SunProtection"]
    assert sun["pset"] == "ePset_SunProtection"
    assert sun["allowed_values"] == "pragmaticbim:value/sun-protection"
    assert BPS_WORKFLOW in sun["needed_for_workflows"]
    assert TENDER_WORKFLOW in sun["needed_for_workflows"]


def test_interior_window_does_not_have_sun_protection() -> None:
    interior = _load("elements/architecture-window-interior.yaml")
    names = {attribute["name"] for attribute in interior["attributes"]}
    assert "SunProtection" not in names


def _profile_xy_bounds(solid) -> tuple[float, float, float, float]:
    position = solid.Position.Location.Coordinates
    ox, oy = float(position[0]), float(position[1])
    points = solid.SweptArea.OuterCurve.Points
    xs = [float(point.Coordinates[0]) + ox for point in points]
    ys = [float(point.Coordinates[1]) + oy for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def test_shading_device_generator_creates_parallel_lamellas_above_the_window() -> None:
    entry = next(item for item in SAMPLE_CATALOG if item["id"] == "shading-device-01")
    ifc_file, shading = generate_shading(map_shading_device_params(entry))

    assert shading.is_a("IfcShadingDevice")
    assert shading.PredefinedType == "JALOUSIE"
    assert ifc_file.by_type("IfcWindow")

    representations = shading.Representation.Representations
    items = [item for rep in representations for item in (rep.Items or [])]
    solids = [item for item in items if item.is_a("IfcExtrudedAreaSolid")]
    assert len(solids) == 6

    def _x_span(solid) -> float:
        x0, x1, _y0, _y1 = _profile_xy_bounds(solid)
        return x1 - x0

    def _y_span(solid) -> float:
        _x0, _x1, y0, y1 = _profile_xy_bounds(solid)
        return y1 - y0

    def _z_span(solid) -> tuple[float, float]:
        z0 = float(solid.Position.Location.Coordinates[2])
        return z0, z0 + float(solid.Depth)

    lamellas = [solid for solid in solids if _x_span(solid) < 0.1 and _y_span(solid) > 0.8]
    beams = [solid for solid in solids if _x_span(solid) > 0.9 and _y_span(solid) < 0.15]
    assert len(lamellas) == 4
    assert len(beams) == 2
    assert all(float(solid.Depth) > 0.3 for solid in lamellas)
    assert all(float(solid.Depth) < 0.15 for solid in beams)

    lamella_z0, lamella_z1 = _z_span(lamellas[0])
    assert lamella_z0 > 2.0
    for beam in beams:
        z0, z1 = _z_span(beam)
        assert lamella_z0 < z0 < z1 <= lamella_z1
    lamella_y0 = _profile_xy_bounds(lamellas[0])[2]
    lamella_y1 = _profile_xy_bounds(lamellas[0])[3]
    beam_edges = sorted(
        (_profile_xy_bounds(solid)[2], _profile_xy_bounds(solid)[3]) for solid in beams
    )
    assert beam_edges[0][1] <= lamella_y0
    assert lamella_y1 <= beam_edges[1][0]

    beam_x1 = max(_profile_xy_bounds(solid)[1] for solid in beams)
    lamella_x1 = max(_profile_xy_bounds(solid)[1] for solid in lamellas)
    assert abs(beam_x1 - lamella_x1) < 1e-6

    lamella_xs = sorted(_profile_xy_bounds(solid)[0] for solid in lamellas)
    gaps = [right - left for left, right in zip(lamella_xs, lamella_xs[1:])]
    assert all(gap > 0.1 for gap in gaps)
