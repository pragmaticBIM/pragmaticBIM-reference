"""Classification and grouping vignettes: eBKP groups, SIA 416 areas, stages, protection zones."""

from __future__ import annotations

import math

import ifcopenshell
from ifcopenshell.api.group import assign_group
from ifcopenshell.api.root import create_entity

from generators.mep_parts import box_solid, duct_solid, pipe_solid

from dataschema.geometry import pyramid
from dataschema.scene import Scene

EBKP_GROUPS = ("ebkp-c", "ebkp-d", "ebkp-e", "ebkp-f", "ebkp-g")
SIA_AREAS = ("sia-hnf", "sia-nnf", "sia-vf", "sia-ff", "sia-kf")

def _ground(s: Scene, x0: float, y0: float, x1: float, y1: float) -> None:
    s.add("IfcGeographicElement", "Terrain", [box_solid(s.ifc_file, x0, y0, -0.35, x1, y1, -0.05)], predefined_type="TERRAIN")


# ---------------------------------------------------------------------------
# eBKP-H: two-storey cut-away building, every element tagged with its main group
# ---------------------------------------------------------------------------

def ebkp() -> Scene:
    """C structure, D services, E facade, F roof, G fit-out."""
    s = Scene.new("eBKP")
    f = s.ifc_file
    _ground(s, -2.0, -2.0, 13.5, 11.0)
    w, d, h = 10.0, 8.0, 3.0

    c = ("ebkp-c",)
    s.add("IfcSlab", "Bodenplatte", [box_solid(f, 0.0, 0.0, -0.3, w, d, 0.0)], keys=c, predefined_type="BASESLAB")
    s.add("IfcSlab", "Decke-OG", [box_solid(f, 0.0, 0.0, h - 0.25, w, d, h)], keys=c, predefined_type="FLOOR")
    for x in (3.5, 7.0):
        for z0 in (0.0, h):
            s.add("IfcColumn", f"Stuetze-{x}-{z0}", [box_solid(f, x - 0.15, 5.0, z0, x + 0.15, 5.3, z0 + h - 0.25)], keys=c, predefined_type="COLUMN")
    s.add("IfcWall", "Kern", [box_solid(f, 0.3, 0.3, 0.0, 2.6, 0.55, 2 * h - 0.25), box_solid(f, 2.35, 0.3, 0.0, 2.6, 2.4, 2 * h - 0.25)], keys=c, predefined_type="SHEAR")

    e = ("ebkp-e",)
    facade_back = [box_solid(f, 0.0, -0.3, -0.3, w, 0.0, 2 * h)]
    facade_side = [box_solid(f, -0.3, -0.3, -0.3, 0.0, d, 2 * h)]
    s.add("IfcWall", "Fassade-Rueckseite", facade_back, keys=e, predefined_type="SOLIDWALL")
    s.add("IfcWall", "Fassade-Seite", facade_side, keys=e, predefined_type="SOLIDWALL")
    for x in (4.0, 6.5, 8.6):
        for z0 in (0.9, h + 0.9):
            s.add("IfcWindow", f"Fenster-{x}-{z0}", [box_solid(f, x - 0.6, 0.0, z0, x + 0.6, 0.08, z0 + 1.4)], keys=e, predefined_type="WINDOW")

    s.add(
        "IfcRoof",
        "Dach",
        [box_solid(f, -0.3, -0.3, 2 * h, w, 3.6, 2 * h + 0.3), box_solid(f, -0.3, 3.4, 2 * h + 0.3, w, 3.6, 2 * h + 0.7)],
        keys=("ebkp-f",),
        predefined_type="FLAT_ROOF",
    )

    dk = ("ebkp-d",)
    s.add("IfcDuctSegment", "Zuluft-EG", [duct_solid(f, (2.8, 1.5, h - 0.55), (w - 0.4, 1.5, h - 0.55), 0.5, 0.3)], keys=dk)
    s.add("IfcPipeSegment", "Steigleitung", [pipe_solid(f, (1.0, 1.4, 0.0), (1.0, 1.4, 2 * h - 0.25), 0.1, segments=12)], keys=dk)
    for x in (4.0, 6.5, 8.6):
        s.add("IfcSpaceHeater", f"Heizkoerper-{x}", [box_solid(f, x - 0.5, 0.05, h + 0.15, x + 0.5, 0.17, h + 0.75)], keys=dk, predefined_type="RADIATOR")
    s.add("IfcUnitaryEquipment", "Lueftungsgeraet", [box_solid(f, 0.6, 1.0, 0.0, 2.1, 2.2, 1.9)], keys=dk, predefined_type="AIRHANDLER")

    g = ("ebkp-g",)
    s.add("IfcWall", "Trennwand-OG", [box_solid(f, 5.2, 0.0, h, 5.32, d, 2 * h - 0.25)], keys=g, predefined_type="PARTITIONING")
    s.add("IfcDoor", "Tuer-OG", [box_solid(f, 5.18, 6.2, h, 5.34, 7.1, h + 2.1)], keys=g, predefined_type="DOOR")
    s.add("IfcCovering", "Bodenbelag-EG", [box_solid(f, 2.6, 0.0, 0.0, w, d, 0.06)], keys=g, predefined_type="FLOORING")
    s.add("IfcCovering", "Bodenbelag-OG", [box_solid(f, 0.0, 0.0, h, w, d, h + 0.06)], keys=g, predefined_type="FLOORING")
    return s


# ---------------------------------------------------------------------------
# SIA 416: one storey with spaces per area category, walls are construction area
# ---------------------------------------------------------------------------

# (key, name, x0, y0, x1, y1) on a 12 x 8 m storey
_ROOMS = (
    ("sia-hnf", "Buero-1", 0.0, 4.8, 4.0, 8.0),
    ("sia-hnf", "Buero-2", 4.0, 4.8, 8.0, 8.0),
    ("sia-hnf", "Buero-3", 8.0, 4.8, 12.0, 8.0),
    ("sia-hnf", "Sitzung", 0.0, 0.0, 5.0, 3.4),
    ("sia-nnf", "Lager", 5.0, 0.0, 7.0, 3.4),
    ("sia-ff", "Technik", 7.0, 0.0, 9.5, 3.4),
    ("sia-vf", "Treppe", 9.5, 0.0, 12.0, 3.4),
    ("sia-vf", "Korridor", 0.0, 3.4, 12.0, 4.8),
)
_W, _D = 12.0, 8.0
_FULL, _CUT, _SPACE = 2.8, 1.1, 2.6


def _plan(s: Scene, cut: float = _CUT) -> dict[str, ifcopenshell.entity_instance]:
    """Back facades full height, front facades and partitions at ``cut`` (low so the spaces read); returns the spaces by name."""
    f = s.ifc_file
    s.add("IfcSlab", "Bodenplatte", [box_solid(f, -0.3, -0.3, -0.3, _W + 1.8, _D + 1.8, 0.0)], predefined_type="BASESLAB")
    kf = ("sia-kf",)
    t, ti = 0.3, 0.12
    s.add("IfcWall", "Aussenwand-Rueck", [box_solid(f, -t, -t, 0.0, _W + t, 0.0, _FULL)], keys=kf, predefined_type="SOLIDWALL")
    s.add("IfcWall", "Aussenwand-Seite", [box_solid(f, -t, 0.0, 0.0, 0.0, _D + t, _FULL)], keys=kf, predefined_type="SOLIDWALL")
    s.add("IfcWall", "Aussenwand-Vorne", [box_solid(f, 0.0, _D, 0.0, _W + t, _D + t, cut)], keys=kf, predefined_type="SOLIDWALL")
    s.add("IfcWall", "Aussenwand-Rechts", [box_solid(f, _W, 0.0, 0.0, _W + t, _D, cut)], keys=kf, predefined_type="SOLIDWALL")
    partitions = [
        box_solid(f, 0.0, 3.4 - ti / 2, 0.0, _W, 3.4 + ti / 2, cut),
        box_solid(f, 0.0, 4.8 - ti / 2, 0.0, _W, 4.8 + ti / 2, cut),
        *(box_solid(f, x - ti / 2, 0.0, 0.0, x + ti / 2, 3.4, cut) for x in (5.0, 7.0, 9.5)),
        *(box_solid(f, x - ti / 2, 4.8, 0.0, x + ti / 2, _D, cut) for x in (4.0, 8.0)),
    ]
    s.add("IfcWall", "Innenwaende", partitions, keys=kf, predefined_type="PARTITIONING")
    gap = ti / 2 + 0.02
    spaces = {
        name: s.add("IfcSpace", name, [box_solid(f, x0 + gap, y0 + gap, 0.0, x1 - gap, y1 - gap, _SPACE)], keys=(key,), predefined_type="SPACE")
        for key, name, x0, y0, x1, y1 in _ROOMS
    }
    s.volume("sia-hnf", "sia-nnf", "sia-vf", "sia-ff")
    return spaces


def sia416() -> Scene:
    s = Scene.new("SIA 416")
    _plan(s)
    return s


_ZONE_ROOMS = ("Buero-1", "Buero-2", "Buero-3")


def protection_zone() -> Scene:
    """IfcZone grouping the net rooms of the front office unit; the corridor stays outside."""
    s = Scene.new("Schutzzone")
    spaces = _plan(s, cut=_FULL)
    members = [spaces[name] for name in _ZONE_ROOMS]
    zone = create_entity(s.ifc_file, ifc_class="IfcZone", name="Schutzzone 1")
    assign_group(s.ifc_file, products=members, group=zone)
    for space in members:
        s.tag(space, ("schutzzone",))
    s.volume("schutzzone")
    return s


# ---------------------------------------------------------------------------
# Modelleinfuegepunkt Disziplin: inverted pyramid cut into one slice per discipline,
# all tips on the insertion point
# ---------------------------------------------------------------------------

# (key, name) counter-clockwise around the hexagon, starting at the corner facing the camera
_SLICES = (
    ("disziplin-architektur", "Architektur"),
    ("disziplin-tragwerk", "Tragwerk"),
    ("disziplin-hlk", "HLK"),
    ("disziplin-sanitaer", "Sanitaer"),
    ("disziplin-elektro", "Elektro"),
    ("disziplin-sonstiges", "Sonstiges"),
)
# Highlight order picks the red shade (light → deep); neighbouring slices alternate light / deep.
DISCIPLINES = tuple(_SLICES[i][0] for i in (0, 2, 4, 1, 3, 5))


def discipline_insertion_point(radius: float = 1.0, height: float = 1.8) -> Scene:
    s = Scene.new("Modelleinfuegepunkt Disziplin")
    n = len(_SLICES)
    for i, (key, name) in enumerate(_SLICES):
        a0 = math.radians(45.0) + 2 * math.pi * i / n
        a1 = a0 + 2 * math.pi / n
        top = [
            (0.0, 0.0, height),
            (radius * math.cos(a0), radius * math.sin(a0), height),
            (radius * math.cos(a1), radius * math.sin(a1), height),
        ]
        product = s.add(
            "IfcBuildingElementProxy",
            name,
            [pyramid(s.ifc_file, top[::-1], (0.0, 0.0, 0.0))],
            keys=(key,),
            object_type="REFERENCEPOINT",
        )
        product.Description = f"Discipline Reference Point {name}"
    return s


# ---------------------------------------------------------------------------
# Etappe: stage 1 built, stage 2 dotted
# ---------------------------------------------------------------------------

def stages() -> Scene:
    s = Scene.new("Etappen")
    f = s.ifc_file
    _ground(s, -2.0, -2.0, 24.0, 14.0)
    h = 3.2
    for i in range(3):
        s.add("IfcBuildingElementProxy", f"Etappe-1-{i + 1}OG", [box_solid(f, 0.0, 0.0, i * h, 10.0, 10.0, (i + 1) * h)], keys=("etappe-1",), object_type="Geschoss")
    for i in range(4):
        s.add(
            "IfcBuildingElementProxy",
            f"Etappe-2-{i + 1}OG",
            [box_solid(f, 10.0, 0.0, i * h, 21.0, 7.0, (i + 1) * h)],
            keys=("etappe-2",),
            object_type="Geschoss",
            dotted=True,
        )
    return s
