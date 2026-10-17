"""Bewegungsfläche vignette: wet room, sanitary fixtures, floor clearances."""

from __future__ import annotations

import sys
from pathlib import Path

import ifcopenshell.geom

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catalog.mapping import map_movement_clearance_params
from catalog.sample_data import SAMPLE_CATALOG
from generators.movement_clearance import (
    DEFAULT_INTERIOR_DEPTH,
    DEFAULT_INTERIOR_WIDTH,
    DEFAULT_WALL_LEFT,
    DEFAULT_WALL_OTHER,
    generate_movement_clearance,
)


def _plan_bounds(product) -> tuple[float, float, float, float]:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = shape.geometry.verts
    xs = verts[0::3]
    ys = verts[1::3]
    return min(xs), max(xs), min(ys), max(ys)


def _z_bounds(product) -> tuple[float, float]:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, product)
    zs = shape.geometry.verts[2::3]
    return min(zs), max(zs)


def test_movement_clearances_sit_in_a_wet_room() -> None:
    entry = next(item for item in SAMPLE_CATALOG if item["id"] == "movement-clearance-01")
    ifc_file, clearances = generate_movement_clearance(map_movement_clearance_params(entry))

    assert len(clearances) == 1
    clearance = clearances[0]
    assert clearance.Name == "Wendefläche"
    assert clearance.is_a("IfcBuildingElementProxy")
    assert clearance.ObjectType == "Bewegungsfläche"

    names = {proxy.Name for proxy in ifc_file.by_type("IfcBuildingElementProxy")}
    assert {"Waschbecken", "Dusche", "WC", "Wendefläche"} <= names

    x_clear0 = DEFAULT_WALL_LEFT
    x_clear1 = DEFAULT_WALL_LEFT + DEFAULT_INTERIOR_WIDTH
    y_clear0 = DEFAULT_WALL_OTHER
    y_clear1 = DEFAULT_WALL_OTHER + DEFAULT_INTERIOR_DEPTH
    cx0, cx1, cy0, cy1 = _plan_bounds(clearance)
    assert cx0 >= x_clear0 - 1e-6
    assert cx1 <= x_clear1 + 1e-6
    assert cy0 >= y_clear0 - 1e-6
    assert cy1 <= y_clear1 + 1e-6
    assert abs((cx1 - cx0) - 1.2) < 1e-4
    assert abs((cy1 - cy0) - 1.2) < 1e-4
    z0, z1 = _z_bounds(clearance)
    assert abs((z1 - z0) - 1.5) < 1e-4
    assert abs(z0) < 1e-4

    basin = next(
        proxy
        for proxy in ifc_file.by_type("IfcBuildingElementProxy")
        if proxy.Name == "Waschbecken"
    )
    wc = next(
        proxy
        for proxy in ifc_file.by_type("IfcBuildingElementProxy")
        if proxy.Name == "WC"
    )
    cistern = next(
        proxy
        for proxy in ifc_file.by_type("IfcBuildingElementProxy")
        if proxy.Name == "WC-Spuelkasten"
    )
    for fixture in (basin, wc, cistern):
        fx0, fx1, fy0, fy1 = _plan_bounds(fixture)
        overlap_x = cx0 < fx1 - 1e-6 and cx1 > fx0 + 1e-6
        overlap_y = cy0 < fy1 - 1e-6 and cy1 > fy0 + 1e-6
        assert not (overlap_x and overlap_y), fixture.Name

    walls = {wall.Name for wall in ifc_file.by_type("IfcWall")}
    assert "Seitenwand-Rechts" not in walls
    assert {"Rueckwand", "Seitenwand-Links"} <= walls

    shower = next(
        proxy
        for proxy in ifc_file.by_type("IfcBuildingElementProxy")
        if proxy.Name == "Dusche"
    )
    shower_z0, shower_z1 = _z_bounds(shower)
    assert abs(shower_z0 - (-0.02)) < 1e-4
    assert abs(shower_z1) < 1e-4
