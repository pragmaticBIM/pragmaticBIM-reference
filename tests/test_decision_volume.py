"""Entscheidungskörper vignette: one storey and several decision volumes."""

from __future__ import annotations

import sys
from pathlib import Path

import ifcopenshell.geom
import pytest
from ifcopenshell.util.element import get_psets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catalog.mapping import map_decision_volume_params
from catalog.sample_data import SAMPLE_CATALOG
from generators.decision_volume import (
    DEFAULT_PLAN_DEPTH,
    DEFAULT_PLAN_WIDTH,
    DEFAULT_SPLIT_X,
    DEFAULT_WALL_THICKNESS,
    generate_decision_volume,
)


def _plan_bounds(product) -> tuple[float, float, float, float]:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = shape.geometry.verts
    xs = verts[0::3]
    ys = verts[1::3]
    return min(xs), max(xs), min(ys), max(ys)


def _height(product) -> float:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, product)
    zs = shape.geometry.verts[2::3]
    return max(zs) - min(zs)


def test_decision_volumes_sit_in_one_storey() -> None:
    entry = next(item for item in SAMPLE_CATALOG if item["id"] == "decision-volume-01")
    ifc_file, volumes = generate_decision_volume(map_decision_volume_params(entry))

    assert len(volumes) == 3
    by_name = {volume.Name: volume for volume in volumes}
    assert set(by_name) == {"Wandfarbe", "Bodenbelag", "Küchenfront"}
    for volume in volumes:
        assert volume.is_a("IfcBuildingElementProxy")
        assert volume.ObjectType == "Entscheidungskörper"
        assert volume.PredefinedType == "USERDEFINED"

    assert get_psets(by_name["Wandfarbe"])["ePset_Decision"]["DecisionReference"] == "E-014"
    assert get_psets(by_name["Wandfarbe"])["ePset_Decision"]["DecisionStatus"] == "OPEN"
    assert get_psets(by_name["Bodenbelag"])["ePset_Decision"]["DecisionStatus"] == "APPROVED"
    assert get_psets(by_name["Küchenfront"])["ePset_Decision"]["DecisionStatus"] == "SUPERSEDED"

    # Continuous wall bodies; door voids as IfcOpeningElement (not fragmented solids).
    assert len(ifc_file.by_type("IfcWall")) >= 6
    assert len(ifc_file.by_type("IfcOpeningElement")) == 2

    for volume in volumes:
        x0, x1, y0, y1 = _plan_bounds(volume)
        assert 0.0 < x0 < x1 < DEFAULT_PLAN_WIDTH
        assert 0.0 < y0 < y1 < DEFAULT_PLAN_DEPTH
        # No short floor-only volume; all Entscheidungströrper share full height.
        assert _height(volume) >= 2.0

    # Wandfarbe reaches the opposite partition; Küchenfront stays clear of it.
    inset = 0.20
    wand_x0, wand_x1, _, _ = _plan_bounds(by_name["Wandfarbe"])
    kueche_x0, kueche_x1, _, _ = _plan_bounds(by_name["Küchenfront"])
    assert wand_x1 == pytest.approx(DEFAULT_SPLIT_X - inset, abs=1e-3)
    assert kueche_x0 > DEFAULT_SPLIT_X + DEFAULT_WALL_THICKNESS
    assert not (wand_x0 < kueche_x1 and kueche_x0 < wand_x1)
