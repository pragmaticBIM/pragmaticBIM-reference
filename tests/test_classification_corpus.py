"""Each classification specimen satisfies the German applicability rule."""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import pytest

from catalog.applicability import german_applicability as _german_applicability
from catalog.applicability import matches_applicability as _matches
from catalog.schema import (
    active_attributes,
    build_element_attributes_from_yaml,
    load_element,
)
from generators.classification_corpus import (
    generate_classification_corpus,
    iter_elements,
)


@pytest.fixture(scope="module")
def corpora() -> dict[str, tuple[ifcopenshell.file, dict[str, ifcopenshell.entity_instance]]]:
    return {
        schema: generate_classification_corpus(schema) for schema in ("ifc4", "ifc2x3")
    }


def test_ifc4_attribute_filter_is_the_default() -> None:
    element = load_element("spaces-interior")
    ifc4_names = {attr["name"] for attr in active_attributes(element)}
    ifc2x3_names = {attr["name"] for attr in active_attributes(element, ifc_schema="ifc2x3")}
    assert "PredefinedType" in ifc4_names
    assert "InteriorOrExteriorSpace" not in ifc4_names
    assert "InteriorOrExteriorSpace" in ifc2x3_names
    assert "PredefinedType" not in ifc2x3_names

    resolved = build_element_attributes_from_yaml(
        entry={},
        element_slug="spaces-interior",
        defaults={"PredefinedType": "SPACE", "IsExternal": False, "Name": "101"},
    )
    assert resolved["PredefinedType"] == "SPACE"
    assert "InteriorOrExteriorSpace" not in resolved.get("direct", {})


def test_corpus_has_one_specimen_per_element(corpora) -> None:
    slugs = [slug for slug, _element in iter_elements()]
    assert len(slugs) == 108
    for schema, (_ifc, specimens) in corpora.items():
        assert set(specimens) == set(slugs), schema


@pytest.mark.parametrize("ifc_schema", ["ifc4", "ifc2x3"])
def test_specimens_satisfy_german_applicability(corpora, ifc_schema: str) -> None:
    _ifc, specimens = corpora[ifc_schema]
    failures: list[str] = []
    for slug, element in iter_elements():
        expression = _german_applicability(element)
        if not expression or f"entity_{ifc_schema}=" not in expression:
            continue
        product = specimens[slug]
        if not _matches(product, expression):
            failures.append(f"{slug}: {expression} [{_snapshot(product)}]")
    assert not failures, "\n".join(failures)


def test_specimens_reuse_example_geometry(corpora) -> None:
    ifc4, specimens = corpora["ifc4"]
    assert "IfcFacetedBrep" in _item_types(specimens["architecture-stair"])
    assert "IfcFacetedBrep" in _item_types(specimens["landscape-tree"])
    assert specimens["site"].Representation is not None
    assert specimens["survey-surface-geometry"].Representation is None
    stairs = [
        product
        for product in ifc4.by_type("IfcStairFlight")
        if product.Description == "architecture-stair"
    ]
    assert len(stairs) == 4
    ducts = [
        product
        for product in ifc4.by_type("IfcDuctSegment")
        if product.Description == "mep-schematic-duct"
    ]
    assert len(ducts) == 1
    gas = [
        product
        for product in ifc4.by_type("IfcProduct")
        if getattr(product, "Description", None) == "mep-gas-terminal"
    ]
    assert [product.is_a() for product in gas] == ["IfcFlowTerminal"]

    _ifc2x3, ifc2x3_specimens = corpora["ifc2x3"]
    assert "IfcFacetedBrep" in _item_types(ifc2x3_specimens["architecture-stair"])
    assert "IfcFacetedBrep" in _item_types(ifc2x3_specimens["landscape-tree"])


@pytest.mark.parametrize("ifc_schema", ["ifc4", "ifc2x3"])
def test_reading_scene_caps_the_office_at_the_suspended_ceiling(corpora, ifc_schema: str) -> None:
    ifc, _specimens = corpora[ifc_schema]
    offices = []
    air_spaces = []
    exteriors = []
    for product in ifc.by_type("IfcSpace"):
        box = _extrusion_box(product)
        if box is None:
            continue
        description = getattr(product, "Description", None)
        if description == "spaces-interior" and _near(box["z1"] - box["z0"], 2.6):
            offices.append((product, box))
        elif description == "spaces-luftraum":
            air_spaces.append((product, box))
        elif description == "spaces-exterior":
            exteriors.append(box)

    paired = [
        (office, air, office_box, air_box)
        for office, office_box in offices
        for air, air_box in air_spaces
        if _same_footprint(office_box, air_box)
        and _near(air_box["z0"], office_box["z1"])
        and _near(air_box["z1"], office_box["z0"] + 3.2)
    ]
    assert len(paired) == 1, ifc_schema
    office, air, office_box, _air_box = paired[0]
    if ifc_schema == "ifc4":
        assert _quantity(office, "Height") == pytest.approx(2.6)
        assert _quantity(office, "NetFloorArea") == pytest.approx(20.0)
        assert _quantity(air, "Height") == pytest.approx(0.6)
        assert _quantity(air, "GrossFloorArea") == pytest.approx(20.0)
    assert any(
        _near(exterior["z1"] - exterior["z0"], 1.0)
        and _near(exterior["ox"], office_box["ox"])
        and _near(exterior["oy"], office_box["oy"])
        and exterior["x1"] <= office_box["x0"] + 1e-4
        for exterior in exteriors
    ), ifc_schema


def _extrusion_box(product: ifcopenshell.entity_instance) -> dict[str, float] | None:
    shape = product.Representation
    if shape is None:
        return None
    item = None
    for representation in shape.Representations:
        if representation.RepresentationIdentifier != "Body" or not representation.Items:
            continue
        candidate = representation.Items[0]
        if candidate.is_a("IfcExtrudedAreaSolid"):
            item = candidate
            break
    if item is None:
        return None
    points = item.SweptArea.OuterCurve.Points
    xs = [float(point.Coordinates[0]) for point in points]
    ys = [float(point.Coordinates[1]) for point in points]
    z0 = float(item.Position.Location.Coordinates[2])
    depth = float(item.Depth)
    placement = ifcopenshell.util.placement.get_local_placement(product.ObjectPlacement)
    return {
        "x0": min(xs),
        "x1": max(xs),
        "y0": min(ys),
        "y1": max(ys),
        "z0": z0,
        "z1": z0 + depth,
        "ox": float(placement[0, 3]),
        "oy": float(placement[1, 3]),
    }


def _quantity(product: ifcopenshell.entity_instance, name: str) -> float:
    for props in ifcopenshell.util.element.get_psets(product).values():
        if name in props:
            return float(props[name])
    raise AssertionError(f"{product.Description} has no {name}")


def _near(left: float, right: float) -> bool:
    return abs(left - right) < 1e-4


def _same_footprint(left: dict[str, float], right: dict[str, float]) -> bool:
    return (
        _near(left["ox"], right["ox"])
        and _near(left["oy"], right["oy"])
        and _near(left["x0"], right["x0"])
        and _near(left["x1"], right["x1"])
        and _near(left["y0"], right["y0"])
        and _near(left["y1"], right["y1"])
    )


def _item_types(product: ifcopenshell.entity_instance) -> set[str]:
    shape = product.Representation
    if shape is None:
        return set()
    return {
        item.is_a()
        for representation in shape.Representations
        for item in representation.Items
    }


def _snapshot(product: ifcopenshell.entity_instance) -> str:
    predefined = getattr(product, "PredefinedType", None)
    object_type = getattr(product, "ObjectType", None)
    return f"{product.is_a()} PredefinedType={predefined!r} ObjectType={object_type!r}"
