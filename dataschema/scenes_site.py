"""Site installations (Umgebung): water supply, wastewater, treatment plant, energy, perimeter access
and a toilet block.

Buried scenes use dotted ground (as the civil vignettes) with the building at the back (y < 0);
cards frame one element each with ``camera_focus``.
"""

from __future__ import annotations

from generators.mep_parts import box_solid, pipe_solid, vertical_cylinder_solid
from generators.parts import rect_polyline
from generators.slab import add_slab

from dataschema.geometry import annular_sector
from dataschema.scene import Scene
from dataschema.scenes_civil import chamber_box, chamber_round
from dataschema.scenes_rooms import corner_room, polyline_solids

WELL = "d08-02-006-brunnenanlage"
RAINWATER = "d08-02-007-regenwassernutzungsanlage"
SPRING_CHAMBER = "i05-05-004-brunnenstube"
RESERVOIR = "i05-05-006-reservoire"

CESSPIT = "d09-02-001-fakaliengrube"
WASTEWATER_PIT = "i05-05-007-abwassergruben"
TREATMENT_SMALL = "i05-05-002-klaranlage-kat-1"
TREATMENT_LARGE = "i05-05-003-klaranlage-kat-2"

HEAT_PLANT = "i05-03-001-warmeanlage"
GROUND_PROBES = "i05-03-002-erdsonden"

BARRIER = "i02-08-004-automatische-barriere"
GATE_AUTOMATIC = "i02-08-006-automatische-umgebungstore"
GATE_MANUAL = "i02-08-007-manuelle-umgebungstore"
DOOR_AUTOMATIC = "i02-08-008-automatische-umgebungsturen"

TOILETS = "i05-05-008-toilettenanlagen"


def _ground(name: str, length: float, depth: float, ground_depth: float, building: tuple[float, float] | None = (1.0, 9.0)) -> Scene:
    s = Scene.new(name, storey_name="Terrain")
    f = s.ifc_file
    s.add("IfcGeographicElement", "Erdreich", [box_solid(f, 0.0, 0.0, -ground_depth, length, depth, 0.0)], predefined_type="TERRAIN", dotted=True)
    if building:
        x0, x1 = building
        s.add("IfcWall", "Gebaeude", [box_solid(f, x0, -5.0, -2.5, x1, 0.0, 6.0)], predefined_type="NOTDEFINED")
    return s


def _pipe(s: Scene, name: str, points, r: float, keys=(), serves=(), segments: int = 10) -> None:
    s.add("IfcPipeSegment", name, polyline_solids(s.ifc_file, points, r, segments=segments), keys=keys, serves=serves, predefined_type="RIGIDSEGMENT", thin=True)


def _ring(f, cx: float, cy: float, z0: float, z1: float, r: float, wall: float = 0.25) -> list:
    return [annular_sector(f, cx, cy, z0, z1, r - wall, r, a, a + 180.0, segments=18) for a in (0.0, 180.0)]


# ---------------------------------------------------------------------------
# Wasserversorgung: well, rainwater, spring chamber, reservoir
# ---------------------------------------------------------------------------


def site_water() -> Scene:
    s = _ground("Wasserversorgung", 27.0, 11.0, 5.4)
    f = s.ifc_file

    keys = (WELL,)
    wx, wy = 4.5, 4.0
    chamber_round(s, "Brunnenkopf", wx, wy, 0.75, -1.8, keys=keys)
    s.add("IfcPipeSegment", "Brunnenrohr", [pipe_solid(f, (wx, wy, -5.2), (wx, wy, -1.8), 0.2, segments=14)], keys=keys, predefined_type="RIGIDSEGMENT")
    s.add("IfcPipeSegment", "Filterrohr", [pipe_solid(f, (wx, wy, -5.2), (wx, wy, -3.8), 0.24, segments=14)], keys=keys, predefined_type="USERDEFINED", object_type="Filterrohr")
    s.add("IfcPump", "Unterwasserpumpe", [pipe_solid(f, (wx, wy, -4.6), (wx, wy, -3.9), 0.12, segments=12)], keys=keys)
    _pipe(s, "Brunnenleitung", [(wx, wy - 0.75, -1.2), (wx, 0.0, -1.2)], 0.06, serves=keys)

    keys = (RAINWATER,)
    _pipe(s, "Fallrohr", [(8.4, 0.15, 6.0), (8.4, 0.15, -0.8), (8.4, 1.2, -0.9)], 0.06, serves=keys)
    chamber_round(s, "Filterschacht", 8.4, 1.6, 0.4, -1.4, keys=keys, ifc_class="IfcFilter", predefined="WATERFILTER")
    s.add("IfcTank", "Zisterne", [box_solid(f, 9.6, 0.8, -3.2, 13.6, 3.2, -1.0), vertical_cylinder_solid(f, 11.6, 2.0, -1.0, 0.35, 0.96, segments=16)], keys=keys, predefined_type="STORAGE")
    _pipe(s, "Zulauf", [(8.8, 1.6, -1.1), (9.6, 1.6, -1.25)], 0.06, serves=keys)
    s.add("IfcPump", "Zisternenpumpe", [pipe_solid(f, (10.2, 1.4, -3.15), (10.2, 1.4, -2.6), 0.12, segments=12)], keys=keys)
    _pipe(s, "Druckleitung", [(10.2, 1.4, -2.6), (10.2, 1.4, -1.5), (10.2, 0.8, -1.5), (10.2, 0.0, -1.5)], 0.04, serves=keys)

    keys = (SPRING_CHAMBER,)
    chamber_box(s, "Brunnenstube", 15.0, 1.0, 18.5, 3.5, -2.6, keys=keys, top=0.4)
    s.add("IfcDoor", "Einstieg", [box_solid(f, 15.2, 3.5, -0.2, 16.4, 4.2, 1.1)], keys=keys, predefined_type="DOOR")
    _pipe(s, "Sickerleitungen", [(12.5, 0.2, -2.0), (15.0, 1.6, -2.2)], 0.07, keys=keys)
    _pipe(s, "Sickerleitung-2", [(16.75, 0.05, -2.0), (16.75, 1.0, -2.2)], 0.07, keys=keys)
    _pipe(s, "Sickerleitung-3", [(21.0, 0.2, -2.0), (18.5, 1.6, -2.2)], 0.07, keys=keys)
    _pipe(s, "Quellleitung", [(18.5, 2.8, -2.3), (20.0, 4.2, -2.6)], 0.08, serves=keys)

    keys = (RESERVOIR,)
    s.add("IfcTank", "Reservoir", [box_solid(f, 20.0, 3.0, -4.4, 26.0, 8.5, -0.8)], keys=keys, predefined_type="STORAGE")
    s.add("IfcBuildingElementProxy", "Schieberhaus", [box_solid(f, 20.0, 8.5, -4.4, 22.8, 10.6, 2.6), box_solid(f, 19.8, 8.3, 2.6, 23.0, 10.8, 2.85)], keys=keys, object_type="Schieberhaus")
    s.add("IfcDoor", "Schieberhaustuer", [box_solid(f, 21.0, 10.6, 0.0, 22.0, 10.65, 2.1)], keys=keys, predefined_type="DOOR")
    s.add("IfcBuildingElementProxy", "Entlueftung", [vertical_cylinder_solid(f, x, 5.8, -0.8, 0.12, 1.6, segments=10) for x in (22.5, 24.5)] + [vertical_cylinder_solid(f, x, 5.8, 0.8, 0.3, 0.15, segments=14) for x in (22.5, 24.5)], keys=keys, object_type="Entlueftung")
    _pipe(s, "Versorgungsleitung", [(22.8, 9.6, -1.4), (27.0, 9.6, -1.4)], 0.1, serves=keys)
    return s


# ---------------------------------------------------------------------------
# Abwasser: cesspit, wastewater pit, compact treatment plant
# ---------------------------------------------------------------------------


def site_wastewater() -> Scene:
    s = _ground("Abwasser-Umgebung", 23.0, 10.0, 4.2)
    f = s.ifc_file

    keys = (CESSPIT,)
    s.add("IfcTank", "Faekaliengrube", [box_solid(f, 2.5, 2.0, -3.0, 6.5, 4.4, -0.8)] + [vertical_cylinder_solid(f, x, 3.2, -0.8, 0.35, 0.86, segments=16) for x in (3.4, 5.6)], keys=keys, predefined_type="STORAGE")
    _pipe(s, "Grubenzulauf", [(3.0, 0.0, -1.0), (3.0, 2.0, -1.15)], 0.08, serves=keys)

    keys = (WASTEWATER_PIT,)
    s.add("IfcSlab", "Waschplatz", [box_solid(f, 7.5, 3.5, -0.05, 11.5, 8.5, 0.05)], predefined_type="USERDEFINED", object_type="Waschplatz", dotted=True)
    s.add("IfcDistributionChamberElement", "Abwassergrube", [box_solid(f, 8.8, 5.2, -2.4, 10.2, 6.8, 0.05)], keys=keys, predefined_type="SUMP")
    s.add("IfcBuildingElementProxy", "Gitterrost", [box_solid(f, 8.8, 5.2, 0.05, 10.2, 6.8, 0.1)], keys=keys, object_type="Gitterrost", dotted=True)
    s.add("IfcPump", "Grubenpumpe", [box_solid(f, 9.2, 5.6, -2.4, 9.6, 6.0, -1.9)], keys=keys)
    _pipe(s, "Grubendruckleitung", [(9.4, 5.8, -1.9), (9.4, 5.8, -1.0), (9.4, 3.2, -1.0), (6.5, 3.2, -1.0)], 0.05, serves=keys)

    keys = (TREATMENT_SMALL,)
    tanks = (14.0, 17.0, 20.0)
    s.add("IfcTank", "Klaerbehaelter", [vertical_cylinder_solid(f, x, 4.5, -3.4, 1.3, 3.0, segments=24) for x in tanks] + [vertical_cylinder_solid(f, x, 4.5, -0.4, 0.35, 0.36, segments=14) for x in tanks], keys=keys, predefined_type="BASIN")
    _pipe(s, "Klaerzulauf", [(6.5, 4.0, -1.3), (12.7, 4.0, -1.3)], 0.08, keys=keys)
    for x in (15.3, 18.3):
        _pipe(s, f"Ueberlauf-{x}", [(x, 4.5, -1.5), (x + 0.4, 4.5, -1.6)], 0.06, keys=keys)
    _pipe(s, "Ablauf", [(21.3, 4.5, -1.8), (23.0, 4.5, -2.0)], 0.08, keys=keys)
    s.add("IfcElectricDistributionBoard", "Klaersteuerung", [box_solid(f, 14.6, 7.4, 0.0, 15.6, 7.8, 1.5)], keys=keys, predefined_type="DISTRIBUTIONBOARD")
    s.add("IfcFan", "Geblaese", [box_solid(f, 16.0, 7.3, 0.0, 16.8, 7.9, 0.7)], keys=keys)
    _pipe(s, "Belueftungsleitung", [(16.4, 7.3, 0.2), (16.4, 7.3, -0.6), (16.6, 5.4, -0.6), (16.6, 4.5, -3.0)], 0.04, keys=keys)
    return s


# ---------------------------------------------------------------------------
# Klaeranlage Kat. 2: open basins
# ---------------------------------------------------------------------------


def treatment_plant() -> Scene:
    """Treatment plant with inlet works, primary clarifier, aeration basins, two secondary clarifiers,
    digester and operations building; open channels connect the stages."""
    s = Scene.new("Klaeranlage", storey_name="Terrain")
    f = s.ifc_file
    add_slab(f, name="Terrain", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, 0.0, 36.0, 22.0), thickness=0.4, z_bottom=-0.4, predefined_type="BASESLAB")
    s.add("IfcBuildingElementProxy", "Betriebsgebaeude", [box_solid(f, 1.0, 13.0, 0.0, 8.0, 20.0, 4.0)], object_type="Betriebsgebaeude")
    keys = (TREATMENT_LARGE,)
    s.add("IfcBuildingElementProxy", "Rechengebaeude", [box_solid(f, 1.0, 2.0, 0.0, 6.0, 7.0, 3.5)], keys=keys, object_type="Rechengebaeude")
    s.add("IfcTank", "Vorklaerbecken", _ring(f, 11.5, 4.5, 0.0, 1.4, 3.5), keys=keys, predefined_type="BASIN")
    walls = [box_solid(f, 17.0, 1.0, 0.0, 29.0, 1.3, 1.4), box_solid(f, 17.0, 8.0, 0.0, 29.0, 8.3, 1.4), box_solid(f, 17.0, 1.0, 0.0, 17.3, 8.3, 1.4), box_solid(f, 28.7, 1.0, 0.0, 29.0, 8.3, 1.4), box_solid(f, 17.0, 4.5, 0.0, 29.0, 4.8, 1.4)]
    s.add("IfcTank", "Belebungsbecken", walls, keys=keys, predefined_type="BASIN")
    for i, (cx, cy) in enumerate(((15.0, 15.5), (24.5, 15.5)), start=1):
        s.add("IfcTank", f"Nachklaerbecken-{i}", _ring(f, cx, cy, 0.0, 1.4, 4.0), keys=keys, predefined_type="BASIN")
        s.add("IfcBuildingElementProxy", f"Raeumerbruecke-{i}", [box_solid(f, cx - 0.4, cy - 0.4, 1.4, cx + 0.4, cy + 0.4, 2.2), box_solid(f, cx, cy - 0.5, 1.6, cx + 4.0, cy + 0.5, 1.9)], keys=keys, object_type="Raeumerbruecke")
    s.add("IfcBuildingElementProxy", "Raeumerbruecke-VKB", [box_solid(f, 11.1, 4.1, 1.4, 11.9, 4.9, 2.2), box_solid(f, 11.5, 4.0, 1.6, 15.0, 5.0, 1.9)], keys=keys, object_type="Raeumerbruecke")
    s.add("IfcTank", "Faulturm", [vertical_cylinder_solid(f, 33.0, 6.0, 0.0, 2.4, 8.0, segments=28), vertical_cylinder_solid(f, 33.0, 6.0, 8.0, 1.2, 0.8, segments=20)], keys=keys, predefined_type="STORAGE")
    channels = [
        box_solid(f, 6.0, 4.1, 0.0, 8.0, 4.9, 0.9),
        box_solid(f, 15.0, 4.1, 0.0, 17.0, 4.9, 0.9),
        box_solid(f, 22.6, 8.3, 0.0, 23.4, 11.5, 0.9),
        box_solid(f, 16.0, 11.5, 0.0, 23.4, 12.3, 0.9),
    ]
    s.add("IfcBuildingElementProxy", "Gerinne", channels, keys=keys, object_type="Gerinne")
    s.add("IfcFan", "Geblaesehaus", [box_solid(f, 29.6, 1.5, 0.0, 31.0, 4.0, 2.4)], keys=keys)
    return s


# ---------------------------------------------------------------------------
# Energie: heat plant, ground probes
# ---------------------------------------------------------------------------


def site_energy() -> Scene:
    s = _ground("Energie-Umgebung", 22.0, 10.0, 10.0)
    f = s.ifc_file

    keys = (HEAT_PLANT,)
    s.add("IfcBuildingElementProxy", "Heizzentrale", [box_solid(f, 14.0, 3.0, 0.0, 20.0, 8.0, 4.0), box_solid(f, 13.8, 2.8, 4.0, 20.2, 8.2, 4.3)], keys=keys, object_type="Heizzentrale")
    s.add("IfcChimney", "Kamin", [vertical_cylinder_solid(f, 19.0, 4.0, 4.3, 0.35, 5.5, segments=16)], keys=keys)
    s.add("IfcDoor", "Tor", [box_solid(f, 15.0, 8.0, 0.0, 17.5, 8.05, 3.0)], keys=keys, predefined_type="GATE")
    for i, dy in enumerate((-0.3, 0.3)):
        _pipe(s, f"Fernwaermeleitung-{i + 1}", [(14.0, 5.5 + dy, -1.0), (7.5 + dy, 5.5 + dy, -1.0), (7.5 + dy, 0.0, -1.0)], 0.1, keys=keys)

    keys = (GROUND_PROBES,)
    probes = [(x, y) for x in (2.0, 4.0, 6.0) for y in (3.5, 6.5)]
    s.add("IfcPipeSegment", "Erdsonden", [pipe_solid(f, (x + dx, y, -9.6), (x + dx, y, -1.4), 0.04, segments=8) for x, y in probes for dx in (-0.06, 0.06)], keys=keys, predefined_type="FLEXIBLESEGMENT", thin=True)
    s.add("IfcPipeFitting", "Sondenfuesse", [pipe_solid(f, (x - 0.1, y, -9.7), (x + 0.1, y, -9.7), 0.06, segments=8) for x, y in probes], keys=keys, predefined_type="BEND", thin=True)
    for y in (3.5, 6.5):
        _pipe(s, f"Sammelleitung-{y}", [(2.0, y, -1.4), (6.0, y, -1.4), (8.0, y, -1.2), (8.6, 2.2, -1.2)], 0.06, keys=keys)
    chamber_round(s, "Verteilerschacht", 9.0, 2.0, 0.6, -1.8, keys=keys)
    _pipe(s, "Sondenzuleitung", [(9.0, 1.4, -1.2), (9.0, 0.0, -1.2)], 0.08, keys=keys)
    return s


# ---------------------------------------------------------------------------
# Umgebungsabschluesse: barrier, gates, door in a perimeter fence
# ---------------------------------------------------------------------------


def _bars(f, x0: float, x1: float, y: float, z0: float, z1: float, spacing: float = 0.2) -> list:
    solids = [box_solid(f, x0, y - 0.04, z0, x1, y + 0.04, z0 + 0.08), box_solid(f, x0, y - 0.04, z1 - 0.08, x1, y + 0.04, z1)]
    solids += [box_solid(f, x, y - 0.04, z0, x + 0.06, y + 0.04, z1) for x in (x0, x1 - 0.06)]
    x = x0 + spacing
    while x < x1 - 0.1:
        solids.append(box_solid(f, x, y - 0.015, z0, x + 0.03, y + 0.015, z1))
        x += spacing
    return solids


def site_access() -> Scene:
    s = Scene.new("Umgebungsabschluss", storey_name="Terrain")
    f = s.ifc_file
    fy, fh = 7.0, 2.2
    add_slab(f, name="Terrain", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, 0.0, 30.0, 14.0), thickness=0.4, z_bottom=-0.4, predefined_type="BASESLAB")
    s.add("IfcBuildingElementProxy", "Zufahrten", [box_solid(f, 3.8, 0.0, 0.0, 9.2, 14.0, 0.05), box_solid(f, 11.8, 0.0, 0.0, 17.2, 14.0, 0.05)], object_type="Strasse")
    s.add("IfcBuildingElementProxy", "Pfoertnerloge", [box_solid(f, 0.8, 8.2, 0.0, 3.2, 10.6, 2.8), box_solid(f, 0.6, 8.0, 2.8, 3.4, 10.8, 3.0)], object_type="Pfoertnerloge")

    openings = ((3.8, 9.2), (11.8, 17.2), (20.0, 24.0), (26.0, 27.2))
    fence_runs = []
    x = 0.0
    for a, b in openings:
        fence_runs.append((x, a))
        x = b
    fence_runs.append((x, 30.0))
    posts, mesh = [], []
    for a, b in fence_runs:
        n = max(1, round((b - a) / 2.5))
        for i in range(n + 1):
            px = a + (b - a) * i / n
            posts.append(box_solid(f, px - 0.04, fy - 0.04, 0.0, px + 0.04, fy + 0.04, fh))
        mesh.append(box_solid(f, a, fy - 0.01, 0.05, b, fy + 0.01, fh - 0.05))
    s.add("IfcBuildingElementProxy", "Zaunpfosten", posts, object_type="Zaunpfosten", thin=True)
    s.add("IfcBuildingElementProxy", "Zaungitter", mesh, object_type="Zaungitter", dotted=True)

    keys = (BARRIER,)
    s.add("IfcActuator", "Schrankenantrieb", [box_solid(f, 4.0, fy + 0.1, 0.0, 4.4, fy + 0.5, 1.1)], keys=keys, predefined_type="ELECTRICACTUATOR")
    s.add("IfcBuildingElementProxy", "Schrankenbaum", [box_solid(f, 4.4, fy + 0.25, 0.85, 9.0, fy + 0.35, 1.0), box_solid(f, 8.85, fy + 0.2, 0.0, 8.95, fy + 0.4, 0.85)], keys=keys, object_type="Schrankenbaum")
    s.add("IfcSensor", "Schrankenleser", [box_solid(f, 5.0, fy + 2.5, 0.0, 5.12, fy + 2.62, 1.2)], keys=keys, predefined_type="IDENTIFIERSENSOR")

    keys = (GATE_AUTOMATIC,)
    s.add("IfcDoor", "Schiebetor", _bars(f, 11.8, 17.2, fy + 0.15, 0.1, fh), keys=keys, predefined_type="GATE", thin=True)
    s.add("IfcBuildingElementProxy", "Gegengewicht", [box_solid(f, 9.4, fy + 0.11, 0.1, 11.8, fy + 0.19, 0.3), box_solid(f, 9.4, fy + 0.11, 0.1, 9.5, fy + 0.19, 1.0)], keys=keys, object_type="Torschwanz")
    s.add("IfcActuator", "Torantrieb", [box_solid(f, 10.6, fy + 0.3, 0.0, 11.2, fy + 0.7, 0.7)], keys=keys, predefined_type="ELECTRICACTUATOR")
    s.add("IfcSensor", "Lichtschranken", [box_solid(f, x, fy + 0.5, 0.0, x + 0.12, fy + 0.62, 0.7) for x in (11.6, 17.3)], keys=keys, predefined_type="MOVEMENTSENSOR")

    keys = (GATE_MANUAL,)
    s.add("IfcDoor", "Fluegeltor", _bars(f, 20.0, 21.98, fy, 0.1, fh) + _bars(f, 22.02, 24.0, fy, 0.1, fh), keys=keys, predefined_type="GATE", thin=True)
    s.add("IfcBuildingElementProxy", "Torbeschlaege", [box_solid(f, 21.85, fy - 0.1, 1.0, 22.15, fy + 0.1, 1.15), box_solid(f, 21.9, fy + 0.05, 0.0, 21.95, fy + 0.1, 0.9)], keys=keys, object_type="Torbeschlag")

    keys = (DOOR_AUTOMATIC,)
    s.add("IfcDoor", "Personentuer", _bars(f, 26.05, 27.15, fy, 0.05, 2.0, spacing=0.15), keys=keys, predefined_type="DOOR", thin=True)
    s.add("IfcActuator", "Tuerantrieb", [box_solid(f, 26.0, fy - 0.1, 2.0, 27.2, fy + 0.15, 2.2)], keys=keys, predefined_type="ELECTRICACTUATOR")
    s.add("IfcSensor", "Ausweisleser", [box_solid(f, 27.5, fy + 0.4, 0.0, 27.62, fy + 0.52, 1.2)], keys=keys, predefined_type="IDENTIFIERSENSOR")
    return s


# ---------------------------------------------------------------------------
# Toilettenanlage
# ---------------------------------------------------------------------------


def toilet_block() -> Scene:
    """Public toilet block: three WC cubicles, urinals, washbasins with hand dryer."""
    s = corner_room("Toilettenanlage", width=7.0, depth=4.5, height=3.0)
    f = s.ifc_file
    keys = (TOILETS,)
    cubicle, d = 1.2, 1.6
    s.add("IfcWall", "Trennwaende", [box_solid(f, i * cubicle - 0.03, 0.0, 0.15, i * cubicle + 0.03, d, 2.1) for i in (1, 2, 3)], predefined_type="PARTITIONING")
    s.add("IfcDoor", "WC-Tueren", [box_solid(f, (i + 1) * cubicle - 0.08, d - 0.75, 0.15, (i + 1) * cubicle - 0.04, d - 0.05, 2.1) for i in range(3)], predefined_type="DOOR")
    s.add(
        "IfcSanitaryTerminal",
        "WC",
        [part for i in range(3) for part in (box_solid(f, i * cubicle + 0.42, 0.0, 0.0, i * cubicle + 0.78, 0.65, 0.42), box_solid(f, i * cubicle + 0.35, 0.0, 0.85, i * cubicle + 0.85, 0.15, 1.15))],
        keys=keys,
        predefined_type="TOILETPAN",
    )
    s.add("IfcSanitaryTerminal", "Urinale", [box_solid(f, x, 0.0, 0.5, x + 0.4, 0.35, 1.2) for x in (4.2, 5.0, 5.8)], keys=keys, predefined_type="URINAL")
    s.add("IfcWall", "Urinaltrennwaende", [box_solid(f, x - 0.02, 0.0, 0.5, x + 0.02, 0.45, 1.6) for x in (4.9, 5.7)], predefined_type="PARTITIONING")
    s.add("IfcSanitaryTerminal", "Waschtische", [box_solid(f, 0.0, y, 0.75, 0.5, y + 0.55, 0.9) for y in (2.4, 3.3)], keys=keys, predefined_type="WASHHANDBASIN")
    s.add("IfcBuildingElementProxy", "Spiegel", [box_solid(f, 0.0, 2.3, 1.2, 0.02, 4.0, 2.0)], object_type="Spiegel")
    s.add("IfcElectricAppliance", "Haendetrockner", [box_solid(f, 0.0, 4.15, 1.0, 0.25, 4.45, 1.4)], predefined_type="HANDDRYER")
    return s
