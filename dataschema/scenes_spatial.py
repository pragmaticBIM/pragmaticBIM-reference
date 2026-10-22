"""Spatial structure vignette (Project / Site / Building / Storey): landscape with trees and two buildings.

Building A is the main building (three storeys, flat roof); building B is smaller
(two storeys, gable roof). Windows face the camera (+X / +Y facades).
"""

from __future__ import annotations

import math

from generators.mep_parts import box_solid, vertical_cylinder_solid
from generators.parts import create_sphere_brep

from dataschema.geometry import profile_x, pyramid
from dataschema.scene import Scene

PROJECT = "project"
SITE = "site"
BUILDING = "building"
STOREY = "storey"

_SITE_KEYS = (PROJECT, SITE)
_WALL_T = 0.3
_SLAB_T = 0.3


def _window(s: Scene, name: str, keys, face: str, at: float, along: float, z0: float, width: float = 1.4, height: float = 1.5) -> None:
    """Window proud of the facade plane ``at`` (``face`` "x" or "y"); black pane in front of a white frame."""
    f = s.ifc_file
    a0, a1 = along - width / 2, along + width / 2
    inset = 0.08
    if face == "x":
        frame = box_solid(f, at, a0, z0, at + 0.06, a1, z0 + height)
        pane = box_solid(f, at + 0.06, a0 + inset, z0 + inset, at + 0.08, a1 - inset, z0 + height - inset)
    else:
        frame = box_solid(f, a0, at, z0, a1, at + 0.06, z0 + height)
        pane = box_solid(f, a0 + inset, at + 0.06, z0 + inset, a1 - inset, at + 0.08, z0 + height - inset)
    s.add("IfcWindow", name, [frame], keys=keys, predefined_type="WINDOW")
    s.add("IfcPlate", f"{name}-Glas", [pane], predefined_type="CURTAIN_PANEL")


def _storey(s: Scene, prefix: str, keys, x0: float, y0: float, x1: float, y1: float, z: float, h: float) -> None:
    """Floor slab plus four exterior walls of one storey."""
    f = s.ifc_file
    t, top = _WALL_T, z + h
    zw = z + _SLAB_T
    s.add("IfcSlab", f"{prefix}-Decke", [box_solid(f, x0, y0, z, x1, y1, zw)], keys=keys, predefined_type="BASESLAB" if z == 0.0 else "FLOOR")
    walls = {
        "Sued": box_solid(f, x0, y0, zw, x1, y0 + t, top),
        "Nord": box_solid(f, x0, y1 - t, zw, x1, y1, top),
        "West": box_solid(f, x0, y0 + t, zw, x0 + t, y1 - t, top),
        "Ost": box_solid(f, x1 - t, y0 + t, zw, x1, y1 - t, top),
    }
    for side, solid in walls.items():
        s.add("IfcWall", f"{prefix}-Wand-{side}", [solid], keys=keys, predefined_type="SOLIDWALL")


def _tree(s: Scene, name: str, x: float, y: float, conifer: bool = False) -> None:
    f = s.ifc_file
    if conifer:
        base = [(x + 1.8 * math.cos(math.radians(a)), y + 1.8 * math.sin(math.radians(a)), 1.0) for a in range(0, 360, 45)]
        solids = [vertical_cylinder_solid(f, x, y, 0.0, 0.18, 1.2, segments=8), pyramid(f, base, (x, y, 7.0))]
    else:
        solids = [vertical_cylinder_solid(f, x, y, 0.0, 0.2, 2.8, segments=8), create_sphere_brep(f, radius=2.0, center=(x, y, 4.3))]
    tree = s.add("IfcGeographicElement", name, solids, keys=_SITE_KEYS, predefined_type="USERDEFINED", object_type="Baum", thin=True)
    tree.Representation.Representations[0].RepresentationType = "SolidModel"


def _building_a(s: Scene) -> None:
    """Three storeys, flat roof; middle storey carries the storey key."""
    f = s.ifc_file
    x0, y0, x1, y1, h, n = 15.0, 4.0, 27.0, 13.0, 3.2, 3
    for i in range(n):
        keys = (PROJECT, BUILDING, STOREY) if i == 1 else (PROJECT, BUILDING)
        z = i * h
        _storey(s, f"A-{i:02d}", keys, x0, y0, x1, y1, z, h)
        sill = z + _SLAB_T + 0.9
        for x in (16.8, 19.7, 22.6, 25.3):
            if i == 0 and x == 19.7:
                continue
            _window(s, f"A-{i:02d}-Fenster-N-{x}", keys, "y", y1, x, sill)
        for y in (5.8, 8.5, 11.2):
            _window(s, f"A-{i:02d}-Fenster-O-{y}", keys, "x", x1, y, sill)
    s.add("IfcDoor", "A-Eingang", [box_solid(f, 19.0, y1, _SLAB_T, 20.4, y1 + 0.08, _SLAB_T + 2.3)], keys=(PROJECT, BUILDING), predefined_type="DOOR")
    top = n * h
    s.add(
        "IfcRoof",
        "A-Flachdach",
        [box_solid(f, x0, y0, top, x1, y1, top + _SLAB_T), box_solid(f, x0, y0, top + _SLAB_T, x1, y0 + 0.25, top + 0.8),
         box_solid(f, x0, y1 - 0.25, top + _SLAB_T, x1, y1, top + 0.8), box_solid(f, x0, y0 + 0.25, top + _SLAB_T, x0 + 0.25, y1 - 0.25, top + 0.8),
         box_solid(f, x1 - 0.25, y0 + 0.25, top + _SLAB_T, x1, y1 - 0.25, top + 0.8)],
        keys=(PROJECT, BUILDING),
        predefined_type="FLAT_ROOF",
    )


def _building_b(s: Scene) -> None:
    """Two storeys, gable roof along X."""
    f = s.ifc_file
    x0, y0, x1, y1, h, n = 4.0, 15.0, 12.0, 22.0, 3.0, 2
    keys = (PROJECT,)
    for i in range(n):
        z = i * h
        _storey(s, f"B-{i:02d}", keys, x0, y0, x1, y1, z, h)
        sill = z + _SLAB_T + 0.9
        for x in (6.0, 10.0):
            _window(s, f"B-{i:02d}-Fenster-N-{x}", keys, "y", y1, x, sill, width=1.2)
        for y in (16.6, 20.4):
            if i == 0 and y == 16.6:
                continue
            _window(s, f"B-{i:02d}-Fenster-O-{y}", keys, "x", x1, y, sill, width=1.2)
    s.add("IfcDoor", "B-Eingang", [box_solid(f, x1, 17.1, _SLAB_T, x1 + 0.08, 18.3, _SLAB_T + 2.2)], keys=keys, predefined_type="DOOR")
    eave, ov, thick = n * h, 0.4, 0.25
    ym = (y0 + y1) / 2
    ridge = eave + 2.6
    s.add("IfcWall", "B-Giebel", [profile_x(f, [(y0, eave), (y1, eave), (ym, ridge)], x, x + _WALL_T) for x in (x0, x1 - _WALL_T)], keys=keys, predefined_type="SOLIDWALL")
    k = (ridge - eave) / (ym - y0)
    lo, hi = y0 - ov, y1 + ov
    roof = [(lo, eave - ov * k), (ym, ridge), (hi, eave - ov * k), (hi, eave - ov * k + thick), (ym, ridge + thick), (lo, eave - ov * k + thick)]
    s.add("IfcRoof", "B-Satteldach", [profile_x(f, roof, x0 - ov, x1 + ov)], keys=keys, predefined_type="GABLE_ROOF")


def spatial_hierarchy() -> Scene:
    """Terrain with paths and trees (site), building A (building, storey) and building B."""
    s = Scene.new("Musterprojekt")
    f = s.ifc_file
    s.add("IfcGeographicElement", "Gelaende", [box_solid(f, 0.0, 0.0, -0.4, 34.0, 26.0, 0.0)], keys=_SITE_KEYS, predefined_type="TERRAIN")
    paths = [
        box_solid(f, 12.08, 17.1, 0.0, 20.4, 18.3, 0.05),
        box_solid(f, 19.0, 13.08, 0.0, 20.4, 17.1, 0.05),
        box_solid(f, 20.4, 17.1, 0.0, 34.0, 18.3, 0.05),
    ]
    s.add("IfcBuildingElementProxy", "Weg", paths, keys=_SITE_KEYS, object_type="Weg")
    for i, (x, y, conifer) in enumerate(((31.0, 9.0, False), (29.5, 22.5, True), (16.0, 22.0, False), (5.5, 7.0, True), (9.5, 3.5, False), (2.5, 12.0, False))):
        _tree(s, f"Baum-{i + 1}", x, y, conifer)
    _building_a(s)
    _building_b(s)
    return s
