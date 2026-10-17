"""Umbauperimeter vignette: decision-model floor plan with one project volume."""

from __future__ import annotations

import sys
from pathlib import Path

import ifcopenshell.geom
import pytest
from ifcopenshell.util.element import get_psets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catalog.mapping import map_umbau_perimeter_params
from catalog.sample_data import SAMPLE_CATALOG
from generators.decision_volume import (
    DEFAULT_PLAN_DEPTH,
    DEFAULT_PLAN_WIDTH,
    DEFAULT_SPLIT_X,
    DEFAULT_WALL_THICKNESS,
)
from generators.umbau_perimeter import generate_umbau_perimeter


def _plan_bounds(product) -> tuple[float, float, float, float]:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = shape.geometry.verts
    xs = verts[0::3]
    ys = verts[1::3]
    return min(xs), max(xs), min(ys), max(ys)


def test_umbau_perimeter_sits_on_decision_storey_plan() -> None:
    entry = next(item for item in SAMPLE_CATALOG if item["id"] == "umbau-perimeter-01")
    ifc_file, perimeter = generate_umbau_perimeter(map_umbau_perimeter_params(entry))

    assert perimeter.is_a("IfcBuildingElementProxy")
    assert perimeter.Name == "P-2026-014"
    assert perimeter.ObjectType == "Umbauperimeter"
    assert perimeter.PredefinedType == "USERDEFINED"
    psets = get_psets(perimeter)
    assert psets["ePset_AlterationArea"]["AlterationStatus"] == "PLANNED"

    assert len(ifc_file.by_type("IfcWall")) >= 6
    assert len(ifc_file.by_type("IfcOpeningElement")) == 2

    x0, x1, y0, y1 = _plan_bounds(perimeter)
    inset = 0.12
    assert x0 == pytest.approx(DEFAULT_WALL_THICKNESS + inset, abs=1e-3)
    assert x1 == pytest.approx(DEFAULT_SPLIT_X - inset, abs=1e-3)
    assert y0 == pytest.approx(DEFAULT_WALL_THICKNESS + inset, abs=1e-3)
    assert y1 == pytest.approx(DEFAULT_PLAN_DEPTH - DEFAULT_WALL_THICKNESS - inset, abs=1e-3)
    assert 0.0 < x0 < x1 < DEFAULT_PLAN_WIDTH
    assert 0.0 < y0 < y1 < DEFAULT_PLAN_DEPTH
