"""Civil network vignettes (Tiefbau): street section with dotted ground so buried parts read.

Shared base: building at the back (y < 0) whose street facade carries the
brand, private yard (0 … 3 m), opaque sidewalk (3 … 4.5 m), road above the
networks (4.5 m … depth). Ground and road are dotted outlines.
"""

from __future__ import annotations

import math

import ifcopenshell

from generators.mep_parts import box_solid, pipe_solid, vertical_cylinder_solid
from generators.parts import create_faceted_brep

from dataschema.scene import Scene

YARD = 3.0
SIDEWALK = 4.5
GROUND_DEPTH = 4.0


def cone_x(f: ifcopenshell.file, x0: float, x1: float, y: float, z: float, r0: float, r1: float, segments: int = 14):
    """Round reducer along X from radius ``r0`` to ``r1``."""
    ring0 = [(x0, y + r0 * math.cos(2 * math.pi * i / segments), z + r0 * math.sin(2 * math.pi * i / segments)) for i in range(segments)]
    ring1 = [(x1, y + r1 * math.cos(2 * math.pi * i / segments), z + r1 * math.sin(2 * math.pi * i / segments)) for i in range(segments)]
    faces = [tuple(reversed(range(segments))), tuple(range(segments, 2 * segments))]
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    return create_faceted_brep(f, [*ring0, *ring1], faces)


def street(name: str, length: float, depth: float = 12.0, building: tuple[float, float] | None = (2.0, 9.0)) -> Scene:
    s = Scene.new(name, storey_name="Terrain")
    f = s.ifc_file
    s.add(
        "IfcGeographicElement",
        "Erdreich",
        [box_solid(f, 0.0, 0.0, -GROUND_DEPTH, length, depth, 0.0)],
        predefined_type="TERRAIN",
        dotted=True,
    )
    s.add("IfcBuildingElementProxy", "Strasse", [box_solid(f, 0.0, SIDEWALK, -0.12, length, depth, 0.0)], object_type="Strasse", dotted=True)
    s.add("IfcSlab", "Trottoir", [box_solid(f, 0.0, YARD, -0.15, length, SIDEWALK, 0.02)], predefined_type="USERDEFINED", object_type="Trottoir")
    if building:
        x0, x1 = building
        s.add("IfcWall", "Gebaeude", [box_solid(f, x0, -5.0, -2.5, x1, 0.0, 6.0)], predefined_type="NOTDEFINED")
    return s


def chamber_round(s: Scene, name: str, cx: float, cy: float, r: float, z_bottom: float, keys=(), ifc_class: str = "IfcDistributionChamberElement", predefined="MANHOLE"):
    f = s.ifc_file
    return s.add(
        ifc_class,
        name,
        [
            vertical_cylinder_solid(f, cx, cy, z_bottom, r, -0.06 - z_bottom, segments=18),
            vertical_cylinder_solid(f, cx, cy, -0.06, r * 0.55, 0.08, segments=18),
        ],
        keys=keys,
        predefined_type=predefined,
    )


def chamber_box(s: Scene, name: str, x0: float, y0: float, x1: float, y1: float, z_bottom: float, keys=(), ifc_class: str = "IfcDistributionChamberElement", predefined="VALVECHAMBER", top: float = -0.04):
    f = s.ifc_file
    cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    return s.add(
        ifc_class,
        name,
        [
            box_solid(f, x0, y0, z_bottom, x1, y1, top),
            box_solid(f, cx - 0.35, cy - 0.35, top, cx + 0.35, cy + 0.35, top + 0.06),
        ],
        keys=keys,
        predefined_type=predefined,
    )


# ---------------------------------------------------------------------------
# Abwasser
# ---------------------------------------------------------------------------

def sewage() -> Scene:
    """Sewer between two manholes with a diameter change, house connection, gutter, infiltration."""
    s = street("Abwasser", 18.0)
    f = s.ifc_file
    y, z = 8.0, -2.6
    run = ("abwasser-haltung-kanal",)
    s.add("IfcPipeSegment", "Haltung-1", [pipe_solid(f, (0.0, y, z), (8.0, y, z), 0.3, segments=16)], keys=run, predefined_type="RIGIDSEGMENT", thin=True)
    s.add("IfcPipeFitting", "Kaliberwechsel", [cone_x(f, 8.0, 8.7, y, z, 0.3, 0.4)], keys=("abwasser-kaliberwechsel",), predefined_type="TRANSITION")
    s.add("IfcPipeSegment", "Haltung-2", [pipe_solid(f, (8.7, y, z), (18.0, y, z), 0.4, segments=16)], keys=run, predefined_type="RIGIDSEGMENT", thin=True)
    for x in (4.0, 13.5):
        chamber_round(s, f"Normalschacht-{x}", x, y, 0.6, z - 0.5, keys=("abwasser-normalschacht",))

    # House connection with an inspection chamber in the yard.
    chamber_round(s, "Kontrollschacht", 6.0, 1.6, 0.45, -1.8, keys=("abwasserkanalschacht",))
    connection = ("abwasser-leitung",)
    s.add("IfcPipeSegment", "Hausanschluss-1", [pipe_solid(f, (6.0, -0.3, -1.1), (6.0, 1.15, -1.3), 0.1, segments=12)], keys=connection, thin=True)
    s.add("IfcPipeSegment", "Hausanschluss-2", [pipe_solid(f, (6.0, 2.05, -1.4), (6.0, y - 0.3, z + 0.15), 0.1, segments=12)], keys=connection, thin=True)

    # Gutter along the road edge, discharging into a gully.
    s.add(
        "IfcPipeSegment",
        "Entwaesserungsrinne",
        [box_solid(f, 8.5, SIDEWALK + 0.05, -0.32, 17.5, SIDEWALK + 0.4, 0.0)],
        keys=("abwasser-entwasserungsrinne",),
        predefined_type="GUTTER",
    )
    s.add("IfcPipeSegment", "Rinnenanschluss", [pipe_solid(f, (16.0, SIDEWALK + 0.22, -0.32), (16.0, y - 0.4, z + 0.2), 0.08, segments=10)])

    # Infiltration box field in the yard fed by a roof downpipe.
    blocks = [
        box_solid(f, 11.0 + i * 1.2, 0.6 + j * 0.9, -1.6, 12.15 + i * 1.2, 1.45 + j * 0.9, -0.7)
        for i in range(4)
        for j in range(2)
    ]
    s.add("IfcBuildingElementProxy", "Versickerung", blocks, keys=("abwasser-versickerungsanlage",), object_type="Versickerungsanlage")
    s.add("IfcPipeSegment", "Regenwasser", [pipe_solid(f, (8.6, -0.2, -0.9), (11.0, 1.4, -1.0), 0.08, segments=10)])
    return s


def sewage_structures() -> Scene:
    """Special sewer structures: storm basin, pumping station, oil separator, throttle structure."""
    s = street("Abwasser-Spezialbauwerke", 20.0)
    f = s.ifc_file
    y, z = 9.0, -3.0
    s.add("IfcPipeSegment", "Kanal", [pipe_solid(f, (0.0, y, z), (20.0, y, z), 0.45, segments=16)], predefined_type="RIGIDSEGMENT")

    chamber_box(s, "Regenbecken", 1.0, 5.2, 7.5, 8.4, -3.6, keys=("abwasser-spezialbauwerk-regenbecken",), predefined="SUMP")
    chamber_box(s, "Pumpwerk", 9.0, 6.0, 11.6, 8.3, -3.8, keys=("abwasser-spezialbauwerk-pumpwerk",), predefined="SUMP")
    s.add("IfcElectricDistributionBoard", "Pumpwerk-Steuerung", [box_solid(f, 9.4, YARD + 0.2, 0.02, 10.6, YARD + 0.6, 1.4)], keys=("abwasser-spezialbauwerk-pumpwerk",), predefined_type="MOTORCONTROLCENTRE")
    s.add("IfcPipeSegment", "Druckleitung", [pipe_solid(f, (10.3, 8.3, -2.0), (10.3, y - 0.4, z + 0.3), 0.12, segments=12)])

    separator = ("abwasser-spezialbauwerk-oelabscheider-schwimmstoffabscheider",)
    s.add("IfcTank", "Oelabscheider", [pipe_solid(f, (12.5, 1.5, -1.9), (16.5, 1.5, -1.9), 0.9, segments=18)], keys=separator, predefined_type="BASIN")
    for x in (13.3, 15.7):
        s.add("IfcTank", f"Abscheider-Dom-{x}", [vertical_cylinder_solid(f, x, 1.5, -1.0, 0.35, 0.96, segments=14)], keys=separator, predefined_type="BASIN")
    s.add("IfcPipeSegment", "Abscheider-Ablauf", [pipe_solid(f, (16.5, 1.5, -2.2), (17.2, y - 0.4, z + 0.3), 0.1, segments=10)])

    chamber_box(s, "Drosselbauwerk", 17.0, 6.2, 19.4, 8.0, -3.4, keys=("abwasser-spezialbauwerk-weitere",), predefined="INSPECTIONCHAMBER")
    s.add("IfcPipeSegment", "Beckenablauf", [pipe_solid(f, (7.5, 6.8, -3.2), (9.0, 6.8, -3.2), 0.3, segments=12)])
    return s


# ---------------------------------------------------------------------------
# Elektrizitaet
# ---------------------------------------------------------------------------

def _street_light(s: Scene, name: str, x: float, y: float, keys, height: float = 6.0) -> None:
    f = s.ifc_file
    s.add(
        "IfcLightFixture",
        name,
        [
            vertical_cylinder_solid(f, x, y, 0.02, 0.08, height, segments=10),
            pipe_solid(f, (x, y, height - 0.1), (x, y + 1.2, height), 0.05, segments=8),
            box_solid(f, x - 0.18, y + 1.0, height - 0.15, x + 0.18, y + 1.6, height + 0.02),
        ],
        keys=keys,
        predefined_type="DIRECTIONSOURCE",
        thin=True,
    )


def electricity(special: bool = False) -> Scene:
    """Buried duct bank with pits, cabinets, street lights, station and an overhead line.

    ``special`` swaps the standard structures for special ones (vault, buried
    substation, cabinet group, charging station).
    """
    s = street("Elektrizitaet", 22.0, building=(2.0, 8.0))
    f = s.ifc_file
    s.add(
        "IfcCableCarrierSegment",
        "Rohrblock",
        [box_solid(f, 0.0, 6.0, -1.2, 22.0, 6.8, -0.6)],
        keys=("elektrizitat-trasse-unterirdisch",),
        predefined_type="CONDUITSEGMENT",
    )

    if not special:
        chamber_box(s, "Kabelschacht", 5.0, 5.6, 6.5, 7.2, -1.8, keys=("elektrizitaet-schacht",), predefined="TRENCH")
        chamber_box(s, "Kabelschacht-2", 14.0, 5.6, 15.5, 7.2, -1.8, keys=("elektrizitaet-schacht",), predefined="TRENCH")
        s.add("IfcDistributionChamberElement", "Verteilkabine", [box_solid(f, 9.0, YARD + 0.3, 0.02, 10.4, YARD + 0.75, 1.3)], keys=("elektrizitaet-kabine",), predefined_type="METERCHAMBER")
        for x in (3.0, 12.0, 19.5):
            _street_light(s, f"Kandelaber-{x}", x, SIDEWALK - 0.3, ("elektrizitaet-oeffentlicher-verbraucher",))
        s.add("IfcBuildingElementProxy", "Trafostation", [box_solid(f, 16.0, 0.4, 0.0, 19.5, 2.6, 2.6)], keys=("elektrizitat-station",), object_type="Trafostation")
        s.add("IfcCableSegment", "Stationsanschluss", [pipe_solid(f, (17.5, 2.6, -0.8), (17.5, 6.0, -0.9), 0.08, segments=8)], thin=True)

        # Overhead line along the road front: masts, crossarms, conductors, guy.
        top = 9.0
        masts = []
        for x in (2.0, 11.0, 20.0):
            masts.append(vertical_cylinder_solid(f, x, 11.4, -1.5, 0.15, top + 1.5, segments=10))
            masts.append(box_solid(f, x - 0.08, 10.6, top - 0.5, x + 0.08, 12.2, top - 0.35))
        s.add("IfcBuildingElementProxy", "Freileitungsmasten", masts, keys=("elektrizitat-tragwerk",), object_type="Mast", thin=True)
        conductors = [pipe_solid(f, (2.0, yy, top - 0.35), (20.0, yy, top - 0.35), 0.03, segments=6) for yy in (10.8, 11.4, 12.0)]
        s.add("IfcCableSegment", "Leiterseile", conductors, keys=("elektrizitat-trasse-oberirdisch",), predefined_type="CONDUCTORSEGMENT", thin=True)
        s.add(
            "IfcBuildingElementProxy",
            "Abspannung",
            [pipe_solid(f, (20.0, 11.4, top - 1.0), (22.0, 11.4, 0.0), 0.04, segments=6), box_solid(f, 21.6, 11.0, -1.2, 22.0, 11.8, -0.6)],
            keys=("elektrizitaet-anker-strebe",),
            object_type="Anker",
            thin=True,
        )
    else:
        chamber_box(s, "Kabelkeller", 0.6, 7.0, 4.0, 10.0, -3.0, keys=("elektrizitaet-spezialbauwerk-schacht",), predefined="TRENCH")
        chamber_box(s, "Unterflurstation", 7.0, 7.4, 11.0, 11.0, -3.2, keys=("elektrizitat-spezialbauwerk-station",), predefined="TRENCH")
        s.add("IfcBuildingElementProxy", "Lueftung-Station", [box_solid(f, 10.2, 10.2, 0.0, 10.8, 10.8, 0.9)], keys=("elektrizitat-spezialbauwerk-station",), object_type="Lueftungsbauwerk")
        s.add(
            "IfcDistributionChamberElement",
            "Kabinengruppe",
            [box_solid(f, 12.5 + i * 0.85, YARD + 0.3, 0.02, 13.3 + i * 0.85, YARD + 0.85, 1.6) for i in range(3)],
            keys=("elektrizitaet-spezialbauwerk-kabine",),
            predefined_type="METERCHAMBER",
        )
        s.add(
            "IfcElectricAppliance",
            "Ladestation",
            [box_solid(f, x, SIDEWALK - 0.6, 0.02, x + 0.45, SIDEWALK - 0.3, 1.6) for x in (17.5, 19.0)],
            keys=("elektrizitat-spezialbauwerk-oeffentlicher-verbraucher",),
            object_type="Ladestation",
        )
        _street_light(s, "Kandelaber", 6.0, SIDEWALK - 0.3, ())
    return s


# ---------------------------------------------------------------------------
# Fernwaerme / Fernkaelte
# ---------------------------------------------------------------------------

def district_energy(network: str = "fernwarme") -> Scene:
    """Buried twin pipe in a trench, valve chamber, pipe bridge, substation and a special structure."""
    s = street("Fernwaerme" if network == "fernwarme" else "Fernkaelte", 20.0)
    f = s.ifc_file
    r = 0.2 if network == "fernwarme" else 0.28
    ys = (7.4, 8.2)
    z = -1.4

    pipes = [pipe_solid(f, (0.0, yy, z), (12.0, yy, z), r, segments=14) for yy in ys]
    s.add("IfcPipeSegment", "Leitung", pipes, keys=(f"{network}-leitung",), predefined_type="RIGIDSEGMENT", thin=True)
    s.add(
        "IfcBuildingElementProxy",
        "Leitungsgraben",
        [box_solid(f, 0.0, ys[0] - 0.6, z - 0.6, 12.0, ys[1] + 0.6, z + 0.6)],
        keys=(f"{network}-trasse-unterirdisch",),
        object_type="Trasse",
    )
    s.volume(f"{network}-trasse-unterirdisch")

    chamber_box(s, "Schieberkammer", 12.0, 6.6, 14.4, 9.0, -2.6, keys=("fernwarme-bauwerk-kammer",))

    # Pipes leave the chamber, rise and cross on a pipe bridge.
    bridge = (f"{network}-trasse-oberirdisch",)
    for yy in ys:
        s.add("IfcPipeSegment", f"Steigleitung-{yy}", [pipe_solid(f, (15.0, yy, -0.5), (15.0, yy, 4.0), r, segments=14)], keys=bridge, thin=True)
        s.add("IfcPipeSegment", f"Bruecke-{yy}", [pipe_solid(f, (15.0, yy, 4.0), (20.0, yy, 4.0), r, segments=14)], keys=bridge, thin=True)
        s.add("IfcPipeSegment", f"Kammeranschluss-{yy}", [pipe_solid(f, (14.4, yy, z), (15.0, yy, z), r, segments=14)])
    supports = []
    for x in (16.5, 19.0):
        supports += [
            box_solid(f, x - 0.12, ys[0] - 0.6, 0.0, x + 0.12, ys[0] - 0.4, 3.75),
            box_solid(f, x - 0.12, ys[1] + 0.4, 0.0, x + 0.12, ys[1] + 0.6, 3.75),
            box_solid(f, x - 0.12, ys[0] - 0.6, 3.6, x + 0.12, ys[1] + 0.6, 3.75),
        ]
    s.add("IfcBuildingElementProxy", "Rohrbruecke", supports, keys=bridge, object_type="Rohrbruecke")

    # Substation in the yard with service pipes from the main.
    station = f"{network}-bauwerk-station"
    s.add("IfcBuildingElementProxy", "Uebergabestation", [box_solid(f, 10.0, 0.4, 0.0, 13.5, 2.6, 2.8)], keys=(station,), object_type="Station")
    for i, yy in enumerate(ys):
        s.add("IfcPipeSegment", f"Hausanschluss-{i}", [pipe_solid(f, (10.6 + i * 0.5, 2.6, -0.9), (10.6 + i * 0.5, yy, z), 0.08, segments=10)])

    # Special structure: buried pumping/pressure vault with access shaft and vent.
    special = (f"{network}-bauwerk-spezialbauwerk",)
    chamber_box(s, "Spezialbauwerk", 1.5, 0.5, 6.0, 2.6, -3.2, keys=special, predefined="VALVECHAMBER")
    s.add("IfcBuildingElementProxy", "Lueftung", [vertical_cylinder_solid(f, 5.4, 1.0, 0.0, 0.18, 1.2, segments=10)], keys=special, object_type="Lueftung")
    return s


# ---------------------------------------------------------------------------
# Gas
# ---------------------------------------------------------------------------

def gas() -> Scene:
    """Gas main in its safety corridor with valve and street cap, chamber, siphon and gas lantern."""
    s = street("Gas", 18.0)
    f = s.ifc_file
    y, z = 8.0, -1.2
    s.add("IfcPipeSegment", "Gasleitung", [pipe_solid(f, (0.0, y, z), (18.0, y, z), 0.18, segments=12)], keys=("gas-leitung",), predefined_type="RIGIDSEGMENT", thin=True)
    s.add(
        "IfcBuildingElementProxy",
        "Sicherheitskorridor",
        [box_solid(f, 0.0, y - 1.0, z - 0.8, 18.0, y + 1.0, -0.02)],
        keys=("gas-sicherheitskorridor",),
        object_type="Sicherheitskorridor",
    )
    s.volume("gas-sicherheitskorridor")

    s.add(
        "IfcValve",
        "Absperrschieber",
        [
            box_solid(f, 5.8, y - 0.25, z - 0.22, 6.2, y + 0.25, z + 0.22),
            vertical_cylinder_solid(f, 6.0, y, z + 0.22, 0.04, -0.12 - (z + 0.22), segments=8),
            vertical_cylinder_solid(f, 6.0, y, -0.12, 0.16, 0.13, segments=14),
        ],
        keys=("gas-absperrorgan",),
        predefined_type="ISOLATING",
    )
    chamber_box(s, "Gasschacht", 10.6, 7.2, 12.2, 8.8, -2.0, keys=("gas-schacht",), predefined="VALVECHAMBER")
    s.add(
        "IfcDistributionChamberElement",
        "Siphon",
        [
            vertical_cylinder_solid(f, 15.0, y, -2.1, 0.22, 0.8, segments=14),
            vertical_cylinder_solid(f, 15.0, y + 0.35, -1.6, 0.04, 1.5, segments=8),
            vertical_cylinder_solid(f, 15.0, y + 0.35, -0.1, 0.14, 0.11, segments=12),
        ],
        keys=("gas-siphon",),
        predefined_type="SUMP",
    )
    s.add(
        "IfcLightFixture",
        "Gaslaterne",
        [
            vertical_cylinder_solid(f, 3.0, SIDEWALK - 0.4, 0.02, 0.09, 3.6, segments=10),
            box_solid(f, 2.75, SIDEWALK - 0.65, 3.6, 3.25, SIDEWALK - 0.15, 4.2),
            box_solid(f, 2.7, SIDEWALK - 0.7, 4.2, 3.3, SIDEWALK - 0.1, 4.3),
        ],
        keys=("gas-gaslaterne",),
        object_type="Gaslaterne",
    )
    s.add("IfcPipeSegment", "Laternenanschluss", [pipe_solid(f, (3.0, SIDEWALK - 0.4, -0.8), (3.0, y, z), 0.04, segments=8)], keys=("gas-gaslaterne",), thin=True)
    s.add("IfcPipeSegment", "Hausanschluss", [pipe_solid(f, (7.5, -0.3, -0.9), (7.5, y, z), 0.05, segments=8)], thin=True)
    return s
