"""Special rooms: extinguishing plant, small cooling rooms, first aid, compressed air and vacuum,
military special installations (H09) and the facade cleaning unit.

Rooms are open-corner rooms (back wall y = 0, side wall x = 0, camera from +X/+Y).
"""

from __future__ import annotations

from generators.mep_parts import box_solid, pipe_solid, vertical_cylinder_solid
from generators.parts import rect_polyline
from generators.slab import add_slab

from dataschema.geometry import frustum, profile_y
from dataschema.scene import Scene
from dataschema.scenes_building import _floor, _wall
from dataschema.scenes_rooms import corner_room, horizontal_cylinder, polyline_solids


def _line(s: Scene, name: str, points, r: float, keys=(), serves=(), ifc_class: str = "IfcPipeSegment", segments: int = 8) -> None:
    predefined = "CABLESEGMENT" if ifc_class == "IfcCableSegment" else None
    s.add(ifc_class, name, polyline_solids(s.ifc_file, points, r, segments=segments), keys=keys, serves=serves, predefined_type=predefined, thin=True)


def _legs(f, x0: float, y0: float, x1: float, y1: float, z1: float, size: float = 0.04) -> list:
    return [box_solid(f, x, y, 0.0, x + size, y + size, z1) for x in (x0, x1 - size) for y in (y0, y1 - size)]


# ---------------------------------------------------------------------------
# Loeschzentrale: powder system, halon extract, fire main
# ---------------------------------------------------------------------------

POWDER = "d04-04-002-pulverloschanlage"
HALON_EXTRACT = "d04-06-003-halonabzugsanlage"
FIRE_MAIN = "d08-01-001-loschleitungen-wenn-nicht-in-d4-3-erfasst"


def extinguishing_plant_room() -> Scene:
    """Extinguishing plant room: powder container fed by propellant cylinders with nozzles under the
    ceiling; floor-level extract for heavy extinguishing gas with its fan; fire main riser with a
    landing valve and a ceiling branch.
    """
    s = corner_room("Loeschzentrale")
    f = s.ifc_file

    # Powder system: propellant cylinders on the side wall -> release valve -> container -> nozzles.
    keys = (POWDER,)
    tx, ty = 1.0, 0.75
    s.add(
        "IfcTank",
        "Pulverbehaelter",
        [
            vertical_cylinder_solid(f, tx, ty, 0.45, 0.5, 1.4, segments=24),
            frustum(f, tx, ty, 0.45, 0.15, (0.35, 0.35), (0.1, 0.1)),
            *(box_solid(f, tx + dx - 0.03, ty + dy - 0.03, 0.0, tx + dx + 0.03, ty + dy + 0.03, 0.5) for dx, dy in ((0.33, 0.33), (-0.33, 0.33), (0.33, -0.33), (-0.33, -0.33))),
        ],
        keys=keys,
        predefined_type="PRESSUREVESSEL",
        object_type="Pulverbehaelter",
    )
    cylinders_y = (1.6, 1.9, 2.2)
    s.add(
        "IfcTank",
        "Treibgasflaschen",
        [part for y in cylinders_y for part in (vertical_cylinder_solid(f, 0.15, y, 0.0, 0.12, 1.4, segments=16), vertical_cylinder_solid(f, 0.15, y, 1.4, 0.05, 0.1, segments=10))],
        keys=keys,
        predefined_type="PRESSUREVESSEL",
        object_type="Treibgasflasche",
    )
    s.add(
        "IfcPipeSegment",
        "Treibgassammler",
        [pipe_solid(f, (0.15, y, 1.5), (0.15, y, 1.65), 0.02, segments=8) for y in cylinders_y]
        + polyline_solids(f, [(0.15, 2.2, 1.65), (0.15, ty, 1.65), (tx - 0.5, ty, 1.65)], 0.025, segments=8),
        keys=keys,
        thin=True,
    )
    s.add("IfcValve", "Ausloeseventil", [box_solid(f, 0.07, 1.17, 1.57, 0.23, 1.33, 1.73), vertical_cylinder_solid(f, 0.15, 1.25, 1.73, 0.05, 0.12, segments=12)], keys=keys, predefined_type="ISOLATING")
    nozzles_x = (2.6, 4.2, 5.8)
    s.add(
        "IfcPipeSegment",
        "Pulverleitung",
        polyline_solids(f, [(tx, ty, 1.85), (tx, ty, 2.7), (tx, 2.2, 2.7), (nozzles_x[-1], 2.2, 2.7)], 0.04, segments=10),
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcFireSuppressionTerminal",
        "Pulverduesen",
        [part for x in nozzles_x for part in (vertical_cylinder_solid(f, x, 2.2, 2.5, 0.03, 0.2, segments=10), frustum(f, x, 2.2, 2.5, 2.4, (0.04, 0.04), (0.1, 0.1)))],
        keys=keys,
        predefined_type="SPRINKLER",
    )
    s.add("IfcUnitaryControlElement", "Loeschsteuerung", [box_solid(f, 0.0, 2.65, 1.1, 0.15, 3.1, 1.8)], keys=keys, predefined_type="CONTROLPANEL")
    _line(s, "Steuerkabel-Pulver", [(0.04, 2.88, 1.8), (0.04, 2.88, 2.85), (0.04, 1.25, 2.85), (0.04, 1.25, 1.75), (0.07, 1.25, 1.75)], 0.012, serves=keys, ifc_class="IfcCableSegment")

    # Floor-level extract for heavy extinguishing gas: low collector duct with grilles, riser, fan.
    keys = (HALON_EXTRACT,)
    s.add("IfcDuctSegment", "Bodenabsaugkanal", [box_solid(f, 3.3, 0.05, 0.1, 5.75, 0.35, 0.5)], keys=keys, predefined_type="RIGIDSEGMENT")
    s.add("IfcAirTerminal", "Absauggitter", [box_solid(f, x, 0.35, 0.15, x + 0.55, 0.38, 0.45) for x in (3.45, 4.25)], keys=keys, predefined_type="GRILLE")
    s.add("IfcDuctSegment", "Absaugsteigkanal", [box_solid(f, 5.45, 0.05, 0.5, 5.75, 0.35, 2.3)], keys=keys, predefined_type="RIGIDSEGMENT")
    s.add(
        "IfcFan",
        "Absaugventilator",
        [box_solid(f, 5.3, 0.0, 2.3, 5.9, 0.5, 2.8), pipe_solid(f, (5.6, 0.5, 2.55), (5.6, 0.56, 2.55), 0.2, segments=20)],
        keys=keys,
        object_type="Absaugventilator",
    )
    s.add("IfcSwitchingDevice", "Absaugschalter", [box_solid(f, 4.9, 0.0, 1.3, 5.15, 0.1, 1.65)], keys=keys, predefined_type="TOGGLESWITCH")
    _line(s, "Kabel-Absaugung", [(5.02, 0.04, 1.65), (5.02, 0.04, 2.55), (5.3, 0.04, 2.55)], 0.012, serves=keys, ifc_class="IfcCableSegment")

    # Fire main: riser on the side wall with isolating valve, landing valve and a ceiling branch.
    keys = (FIRE_MAIN,)
    rx, ry = 0.2, 3.7
    s.add("IfcPipeSegment", "Loeschleitung-Steig", [pipe_solid(f, (rx, ry, -0.25), (rx, ry, 2.75), 0.06, segments=12)], keys=keys, predefined_type="RIGIDSEGMENT")
    s.add("IfcPipeSegment", "Loeschleitung-Abzweig", polyline_solids(f, [(rx, ry, 2.75), (3.2, ry, 2.75)], 0.05, segments=12), keys=keys, predefined_type="RIGIDSEGMENT")
    s.add("IfcValve", "Absperrschieber", [box_solid(f, rx - 0.1, ry - 0.1, 0.4, rx + 0.1, ry + 0.1, 0.65), vertical_cylinder_solid(f, rx, ry, 0.65, 0.02, 0.2, segments=8), pipe_solid(f, (rx - 0.12, ry, 0.88), (rx + 0.12, ry, 0.88), 0.012, segments=6)], keys=keys, predefined_type="ISOLATING")
    s.add(
        "IfcValve",
        "Abgangsventil",
        [pipe_solid(f, (rx, ry, 1.2), (rx + 0.3, ry, 1.2), 0.04, segments=10), pipe_solid(f, (rx + 0.3, ry, 1.2), (rx + 0.36, ry, 1.2), 0.07, segments=14), box_solid(f, rx + 0.1, ry - 0.06, 1.26, rx + 0.2, ry + 0.06, 1.36)],
        keys=keys,
        predefined_type="ISOLATING",
    )
    s.add("IfcFlowInstrument", "Manometer", [pipe_solid(f, (rx, ry, 1.8), (rx + 0.1, ry, 1.8), 0.012, segments=6), pipe_solid(f, (rx + 0.1, ry, 1.8), (rx + 0.13, ry, 1.8), 0.06, segments=14)], keys=keys, predefined_type="PRESSUREGAUGE")
    s.add("IfcFireSuppressionTerminal", "Endkappe", [pipe_solid(f, (3.2, ry, 2.75), (3.28, ry, 2.75), 0.07, segments=14)], keys=keys, predefined_type="BREECHINGINLET")
    return s


# ---------------------------------------------------------------------------
# Buero: split air conditioner
# ---------------------------------------------------------------------------

SPLIT_AC = "d06-02-001-klima-splittgerate"


def split_ac_office() -> Scene:
    """Office cutaway: wall-mounted indoor unit on the side wall, outdoor unit on the roof slab above
    the back corner, refrigerant lines through the roof, condensate drain and wall controller."""
    height = 2.8
    s = corner_room("Buero-Split", width=4.2, depth=3.4, height=height)
    f = s.ifc_file
    keys = (SPLIT_AC,)
    zr = height + 0.25
    add_slab(f, name="Dachplatte", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(-0.2, -0.2, 2.4, 1.6), thickness=zr - height, z_bottom=height, predefined_type="ROOF")

    s.add("IfcFurniture", "Tisch", [box_solid(f, 1.6, 1.9, 0.7, 3.4, 2.7, 0.75), *_legs(f, 1.62, 1.92, 3.38, 2.68, 0.7)], predefined_type="TABLE")
    s.add("IfcFurniture", "Stuhl", [box_solid(f, 2.25, 2.85, 0.42, 2.75, 3.3, 0.47), box_solid(f, 2.25, 3.25, 0.47, 2.75, 3.3, 0.95), vertical_cylinder_solid(f, 2.5, 3.07, 0.0, 0.03, 0.42, segments=8)], predefined_type="CHAIR")

    iy0, iy1, iz0, iz1 = 1.8, 2.8, 2.15, 2.47
    s.add(
        "IfcUnitaryEquipment",
        "Innengeraet",
        [box_solid(f, 0.0, iy0, iz0, 0.22, iy1, iz1), box_solid(f, 0.12, iy0 + 0.05, iz0 - 0.03, 0.24, iy1 - 0.05, iz0)],
        keys=keys,
        predefined_type="SPLITSYSTEM",
    )
    ox0, ox1 = 0.4, 1.4
    s.add("IfcBuildingElementProxy", "Konsole-Aussengeraet", [box_solid(f, ox0, y, zr, ox1, y + 0.06, zr + 0.1) for y in (0.1, 0.44)], keys=keys, object_type="Konsole")
    s.add(
        "IfcUnitaryEquipment",
        "Aussengeraet",
        [box_solid(f, ox0, 0.08, zr + 0.1, ox1, 0.5, zr + 0.8), pipe_solid(f, (0.8, 0.5, zr + 0.45), (0.8, 0.53, zr + 0.45), 0.25, segments=24)],
        keys=keys,
        predefined_type="SPLITSYSTEM",
    )
    for i, dz in enumerate((0.0, 0.06)):
        _line(s, f"Kaeltemittelleitung-{i + 1}", [(0.06, iy0, 2.3 + dz), (0.06, 1.2, 2.3 + dz), (0.06, 1.2, zr + 0.3 + dz), (0.06, 0.3, zr + 0.3 + dz), (ox0, 0.3, zr + 0.3 + dz)], 0.018, keys=keys)
    _line(s, "Kondensatleitung", [(0.06, iy1 - 0.1, iz0), (0.06, iy1 - 0.1, 0.25)], 0.015, keys=keys)
    s.add("IfcUnitaryControlElement", "Raumbediengeraet", [box_solid(f, 0.0, 3.05, 1.35, 0.03, 3.2, 1.5)], keys=keys, predefined_type="THERMOSTAT")
    return s


# ---------------------------------------------------------------------------
# UG-Lager: dehumidifier
# ---------------------------------------------------------------------------

DEHUMIDIFIER = "d06-02-004-entfeuchter"


def dehumidified_store() -> Scene:
    """Basement store with shelving; floor-standing dehumidifier with condensate hose to a floor drain
    and a hygrostat on the back wall."""
    s = corner_room("UG-Lager", width=4.5, depth=3.4, height=2.5)
    f = s.ifc_file
    keys = (DEHUMIDIFIER,)

    shelf = [box_solid(f, 0.05, 0.3, z, 0.6, 2.9, z + 0.03) for z in (0.1, 0.65, 1.2, 1.75)]
    shelf += [box_solid(f, x, y, 0.0, x + 0.04, y + 0.04, 1.9) for x in (0.05, 0.56) for y in (0.3, 1.58, 2.86)]
    s.add("IfcFurniture", "Regal", shelf, predefined_type="SHELF")
    boxes = ((0.4, 0.1), (1.0, 0.1), (2.3, 0.1), (0.4, 0.65), (1.7, 0.65), (1.0, 1.2), (2.3, 1.2), (1.7, 1.75))
    s.add("IfcBuildingElementProxy", "Lagergut", [box_solid(f, 0.1, y, z + 0.03, 0.5, y + 0.45, z + 0.38) for y, z in boxes], object_type="Kiste")

    x0, x1, y0, y1 = 2.4, 3.1, 0.15, 0.55
    s.add(
        "IfcUnitaryEquipment",
        "Luftentfeuchter",
        [
            box_solid(f, x0, y0, 0.12, x1, y1, 1.0),
            *(box_solid(f, x0 + 0.08, y1, z, x1 - 0.08, y1 + 0.02, z + 0.03) for z in (0.6, 0.68, 0.76, 0.84)),
            box_solid(f, x0 + 0.2, y1, 0.3, x1 - 0.2, y1 + 0.02, 0.42),
            *(vertical_cylinder_solid(f, x, y, 0.0, 0.035, 0.12, segments=10) for x in (x0 + 0.06, x1 - 0.06) for y in (y0 + 0.06, y1 - 0.06)),
        ],
        keys=keys,
        predefined_type="DEHUMIDIFIER",
    )
    s.add("IfcWasteTerminal", "Bodenablauf", [box_solid(f, 2.6, 1.05, 0.0, 2.9, 1.35, 0.02)], predefined_type="FLOORTRAP")
    _line(s, "Kondensatschlauch", [(2.75, y1, 0.25), (2.75, 1.2, 0.25), (2.75, 1.2, 0.03)], 0.018, keys=keys)
    s.add("IfcSensor", "Hygrostat", [box_solid(f, 3.6, 0.0, 1.4, 3.75, 0.05, 1.6)], keys=keys, predefined_type="HUMIDITYSENSOR")
    _line(s, "Kabel-Hygrostat", [(3.67, 0.03, 1.4), (3.67, 0.03, 1.1), (3.0, 0.03, 1.1), (3.0, 0.15, 1.0)], 0.01, serves=keys, ifc_class="IfcCableSegment")
    return s


# ---------------------------------------------------------------------------
# Kuechenlager: cold room
# ---------------------------------------------------------------------------

COLD_ROOM = "d06-02-005-kuhlzelle-tiefkuhlzelle"


def cold_room_store() -> Scene:
    """Kitchen store with a walk-in cold room built from insulated panels: door swung open, evaporator
    under the cell ceiling, condensing unit on the cell roof, display controller beside the door."""
    s = corner_room("Kuechenlager", width=5.5, depth=4.0, height=3.0)
    f = s.ifc_file
    keys = (COLD_ROOM,)
    x0, y0, x1, y1, h, t = 0.1, 0.1, 2.7, 2.3, 2.4, 0.1
    d0, d1, dh = 0.8, 1.7, 2.0
    s.add(
        "IfcBuildingElementProxy",
        "Kuehlzellenpaneele",
        [
            box_solid(f, x0, y0, 0.0, x1, y0 + t, h),
            box_solid(f, x0, y0, 0.0, x0 + t, y1, h),
            box_solid(f, x0, y1 - t, 0.0, x1, y1, h),
            box_solid(f, x1 - t, y0, 0.0, x1, d0, h),
            box_solid(f, x1 - t, d1, 0.0, x1, y1, h),
            box_solid(f, x1 - t, d0, dh, x1, d1, h),
            box_solid(f, x0, y0, h - t, x1, y1, h),
        ],
        keys=keys,
        object_type="Kuehlzelle",
    )
    s.add(
        "IfcDoor",
        "Kuehlzellentuer",
        [box_solid(f, x1, d1 - 0.1, 0.02, x1 + 0.9, d1, dh - 0.02), box_solid(f, x1 + 0.7, d1, 0.95, x1 + 0.78, d1 + 0.08, 1.25)],
        keys=keys,
        predefined_type="DOOR",
    )
    s.add("IfcEvaporator", "Verdampfer-Kuehlzelle", [box_solid(f, 0.9, y0 + t, 1.9, 2.0, 0.55, h - t)], keys=keys, predefined_type="DIRECTEXPANSION")
    s.add(
        "IfcCondenser",
        "Verfluessigungssatz",
        [box_solid(f, 0.6, 0.6, h, 1.8, 1.5, h + 0.45), vertical_cylinder_solid(f, 1.2, 1.05, h + 0.45, 0.28, 0.03, segments=20)],
        keys=keys,
        predefined_type="AIRCOOLED",
    )
    s.add("IfcController", "Kuehlstellenregler", [box_solid(f, x1, d1 + 0.15, 1.35, x1 + 0.05, d1 + 0.4, 1.6)], keys=keys)
    _line(s, "Kaeltemittelleitung", [(1.5, 0.55, h - t), (1.5, 0.55, h + 0.2), (1.5, 0.6, h + 0.2)], 0.02, keys=keys)

    s.add("IfcFurniture", "Regal-Kueche", [box_solid(f, x, 0.05, z, x + 2.0, 0.5, z + 0.03) for x in (3.2,) for z in (0.3, 0.9, 1.5)] + _legs(f, 3.2, 0.05, 5.2, 0.5, 1.6), predefined_type="SHELF")
    s.add("IfcFurniture", "Arbeitstisch", [box_solid(f, 3.4, 2.6, 0.85, 5.2, 3.4, 0.9), *_legs(f, 3.42, 2.62, 5.18, 3.38, 0.85)], predefined_type="TABLE")
    return s


# ---------------------------------------------------------------------------
# Sanitaetsraum: medical device
# ---------------------------------------------------------------------------

MEDICAL = "medizinisches-gerat"


def first_aid_room() -> Scene:
    """First-aid room: treatment couch below a medical supply unit with gas outlets, mobile oxygen
    concentrator beside it; sink and wall cabinet as context."""
    s = corner_room("Sanitaetsraum", width=4.5, depth=3.6, height=2.8)
    f = s.ifc_file
    keys = (MEDICAL,)
    s.add(
        "IfcFurniture",
        "Behandlungsliege",
        [box_solid(f, 1.0, 0.2, 0.6, 2.9, 0.85, 0.72), box_solid(f, 2.4, 0.2, 0.72, 2.9, 0.85, 0.9), *_legs(f, 1.05, 0.25, 2.85, 0.8, 0.6)],
        predefined_type="BED",
    )
    s.add("IfcSanitaryTerminal", "Waschtisch", [box_solid(f, 0.0, 2.4, 0.8, 0.5, 3.0, 0.92), box_solid(f, 0.0, 2.55, 0.92, 0.1, 2.85, 1.15)], predefined_type="WASHHANDBASIN")
    s.add("IfcFurniture", "Wandschrank", [box_solid(f, 0.0, 1.2, 1.4, 0.35, 2.1, 2.1)], predefined_type="USERDEFINED", object_type="Wandschrank")

    s.add(
        "IfcMedicalDevice",
        "Medienversorgungseinheit",
        [
            box_solid(f, 0.9, 0.0, 1.25, 3.0, 0.12, 1.5),
            *(pipe_solid(f, (x, 0.12, 1.36), (x, 0.17, 1.36), 0.03, segments=12) for x in (1.2, 1.4, 1.6)),
            box_solid(f, 2.2, 0.12, 1.3, 2.8, 0.15, 1.44),
        ],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Medienversorgungseinheit",
    )
    cx0, cx1, cy0, cy1 = 3.25, 3.65, 0.3, 0.65
    s.add(
        "IfcMedicalDevice",
        "Sauerstoffkonzentrator",
        [
            box_solid(f, cx0, cy0, 0.08, cx1, cy1, 0.75),
            box_solid(f, cx0 + 0.05, cy1, 0.55, cx1 - 0.05, cy1 + 0.02, 0.7),
            *(vertical_cylinder_solid(f, x, y, 0.0, 0.03, 0.08, segments=10) for x in (cx0 + 0.05, cx1 - 0.05) for y in (cy0 + 0.05, cy1 - 0.05)),
        ],
        keys=keys,
        predefined_type="OXYGENGENERATOR",
    )
    _line(s, "Sauerstoffschlauch", [(cx0 + 0.1, cy1, 0.7), (cx0 - 0.1, 0.9, 0.95), (2.7, 0.75, 0.95)], 0.012, keys=keys)
    for i, x in enumerate((1.4, 1.6)):
        _line(s, f"Medizinalgas-{i + 1}", [(x, 0.03, 1.5), (x, 0.03, 2.8)], 0.015, serves=keys)
    return s


# ---------------------------------------------------------------------------
# Druckluftzentrale: refrigerated dryer, vacuum plant
# ---------------------------------------------------------------------------

AIR_DRYER = "d06-02-006-druckluftkaltetrockner"
VACUUM = "d11-02-002-vakuumanlage"


def compressed_air_room() -> Scene:
    """Compressed-air room: screw compressor, refrigerated dryer and air receiver along the back wall;
    vacuum pumps with vacuum receiver and controller along the side wall."""
    s = corner_room("Druckluftzentrale")
    f = s.ifc_file

    s.add("IfcCompressor", "Schraubenkompressor", [box_solid(f, 0.4, 0.15, 0.0, 1.6, 1.0, 1.5), box_solid(f, 0.5, 1.0, 0.8, 1.5, 1.02, 1.3)], predefined_type="ROTARY")
    s.add("IfcTank", "Druckluftbehaelter", [vertical_cylinder_solid(f, 3.6, 0.6, 0.1, 0.4, 1.9, segments=24), *(box_solid(f, 3.6 + dx - 0.03, 0.6 + dy - 0.03, 0.0, 3.6 + dx + 0.03, 0.6 + dy + 0.03, 0.15) for dx, dy in ((0.3, 0.0), (-0.15, 0.25), (-0.15, -0.25)))], predefined_type="PRESSUREVESSEL")
    s.add("IfcPipeSegment", "Druckluftnetz", polyline_solids(f, [(3.95, 0.6, 1.6), (4.3, 0.6, 1.6), (4.3, 0.25, 1.6), (4.3, 0.25, 2.4), (6.3, 0.25, 2.4)], 0.035, segments=10), thin=True)

    keys = (AIR_DRYER,)
    s.add(
        "IfcUnitaryEquipment",
        "Kaeltetrockner",
        [
            box_solid(f, 2.0, 0.15, 0.0, 2.75, 0.85, 1.2),
            vertical_cylinder_solid(f, 2.37, 0.5, 1.2, 0.25, 0.03, segments=20),
            box_solid(f, 2.15, 0.85, 0.85, 2.45, 0.87, 1.05),
        ],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Druckluft-Kaeltetrockner",
    )
    s.add("IfcFilter", "Druckluftfilter", [vertical_cylinder_solid(f, 2.95, 0.45, 1.1, 0.07, 0.4, segments=14)], keys=keys, predefined_type="COMPRESSEDAIRFILTER")
    _line(s, "Druckluft-Eintritt", [(1.0, 0.35, 1.5), (1.0, 0.35, 2.25), (2.2, 0.35, 2.25), (2.2, 0.35, 1.2)], 0.035, serves=keys, segments=10)
    _line(s, "Druckluft-Austritt", [(2.6, 0.45, 1.2), (2.6, 0.45, 1.75), (3.6, 0.45, 1.75), (3.6, 0.6, 2.0)], 0.035, serves=keys, segments=10)
    s.add("IfcWasteTerminal", "Bodenablauf", [box_solid(f, 2.45, 1.35, 0.0, 2.75, 1.65, 0.02)], predefined_type="FLOORTRAP")
    _line(s, "Kondensatableitung", [(2.6, 0.85, 0.15), (2.6, 1.5, 0.15), (2.6, 1.5, 0.03)], 0.015, keys=keys)

    keys = (VACUUM,)
    s.add("IfcBuildingElementProxy", "Grundrahmen-Vakuum", [box_solid(f, 0.15, 2.0, 0.0, 1.05, 3.6, 0.12)], keys=keys, object_type="Grundrahmen")
    pumps = []
    for y in (2.4, 3.2):
        pumps += [horizontal_cylinder(f, 0.25, 0.65, y, 0.35, 0.18, segments=18), horizontal_cylinder(f, 0.65, 0.98, y, 0.35, 0.15, segments=16)]
    s.add("IfcPump", "Vakuumpumpen", pumps, keys=keys, object_type="Vakuumpumpe")
    s.add("IfcTank", "Vakuumbehaelter", [vertical_cylinder_solid(f, 0.55, 4.0, 0.0, 0.3, 1.4, segments=20)], keys=keys, predefined_type="VESSEL")
    s.add("IfcController", "Vakuumsteuerung", [box_solid(f, 0.0, 1.2, 1.0, 0.25, 1.7, 1.8)], keys=keys)
    _line(s, "Vakuumleitung", [(0.45, 2.4, 0.53), (0.45, 2.4, 1.8), (0.45, 4.0, 1.8), (0.45, 4.0, 1.4)], 0.035, keys=keys, segments=10)
    _line(s, "Vakuumanschluss", [(0.45, 3.2, 0.53), (0.45, 3.2, 1.8)], 0.035, keys=keys, segments=10)
    _line(s, "Vakuumnetz", [(0.45, 2.4, 1.8), (0.45, 1.95, 1.8), (0.45, 1.95, 2.6), (0.0, 1.95, 2.6)], 0.035, serves=keys, segments=10)
    _line(s, "Kabel-Vakuum", [(0.12, 1.7, 1.4), (0.12, 2.2, 1.4), (0.12, 2.2, 0.35), (0.25, 2.2, 0.35)], 0.012, serves=keys, ifc_class="IfcCableSegment")
    return s


# ---------------------------------------------------------------------------
# H09: climate chamber, breathing-protection training, target system, gas production
# ---------------------------------------------------------------------------

CLIMATE_CHAMBER = "h09-05-003-temperaturschranke-klimakammer"
BREATHING_COURSE = "h09-05-004-ubungsanlage-atemschutz"
TARGET_SYSTEM = "h09-05-005-automatische-scheibenanlage"
GAS_PRODUCTION = "h09-05-006-gasproduktionsanlage"


def climate_lab() -> Scene:
    """Test laboratory: walk-in climate chamber with door, viewing window, control panel and climate
    unit on the roof; two temperature cabinets on the back wall; lab bench as context."""
    s = corner_room("Klimalabor")
    f = s.ifc_file
    keys = (CLIMATE_CHAMBER,)
    x0, y0, x1, y1, h = 0.15, 0.15, 2.9, 2.6, 2.5
    s.add("IfcBuildingElementProxy", "Klimakammer", [box_solid(f, x0, y0, 0.0, x1, y1, h)], keys=keys, object_type="Klimakammer")
    s.add("IfcDoor", "Kammertuer", [box_solid(f, x1, 0.6, 0.05, x1 + 0.08, 1.6, 2.05), box_solid(f, x1 + 0.08, 1.45, 0.95, x1 + 0.14, 1.52, 1.3)], keys=keys, predefined_type="DOOR")
    s.add("IfcWindow", "Sichtfenster", [box_solid(f, x1, 1.85, 1.0, x1 + 0.03, 2.4, 1.6)], keys=keys, predefined_type="WINDOW")
    s.add("IfcController", "Kammerregler", [box_solid(f, 1.9, y1, 1.1, 2.6, y1 + 0.08, 1.7)], keys=keys)
    s.add("IfcUnitaryEquipment", "Klimaaggregat", [box_solid(f, 0.5, 0.5, h, 2.0, 1.6, h + 0.4), vertical_cylinder_solid(f, 1.25, 1.05, h + 0.4, 0.3, 0.03, segments=20)], keys=keys, predefined_type="USERDEFINED", object_type="Klimaaggregat")
    for i, cx in enumerate((3.6, 4.6), start=1):
        s.add(
            "IfcElectricAppliance",
            f"Temperaturschrank-{i}",
            [box_solid(f, cx, 0.1, 0.0, cx + 0.8, 0.85, 1.9), box_solid(f, cx + 0.08, 0.85, 0.5, cx + 0.72, 0.88, 1.7), box_solid(f, cx + 0.25, 0.88, 1.75, cx + 0.55, 0.9, 1.85)],
            keys=keys,
            predefined_type="USERDEFINED",
            object_type="Temperaturschrank",
        )
    s.add("IfcFurniture", "Labortisch", [box_solid(f, 3.6, 3.4, 0.85, 6.2, 4.2, 0.9), *_legs(f, 3.62, 3.42, 6.18, 4.18, 0.85)], predefined_type="TABLE")
    return s


def breathing_training() -> Scene:
    """Breathing-protection training: two-level steel cage course with a crawl tube, endless ladder,
    treadmill, smoke generator and supervision desk."""
    s = corner_room("Atemschutz-Uebungsanlage", width=7.0, depth=5.0, height=3.2)
    f = s.ifc_file
    keys = (BREATHING_COURSE,)
    xs, ys, zs = (0.3, 1.7, 3.1, 4.5), (0.3, 1.5, 2.7), (0.0, 1.2, 2.4)
    bars = [pipe_solid(f, (x, y, 0.0), (x, y, zs[-1]), 0.025, segments=6) for x in xs for y in ys]
    bars += [pipe_solid(f, (xs[0], y, z), (xs[-1], y, z), 0.02, segments=6) for y in ys for z in zs[1:]]
    bars += [pipe_solid(f, (x, ys[0], z), (x, ys[-1], z), 0.02, segments=6) for x in xs for z in zs[1:]]
    s.add("IfcMember", "Gitterkaefig", bars, keys=keys, predefined_type="MEMBER", thin=True)
    s.add("IfcSlab", "Zwischenboden", [box_solid(f, xs[1], ys[0], 1.17, xs[-1], ys[-1], 1.2)], keys=keys, predefined_type="FLOOR")
    s.add("IfcBuildingElementProxy", "Kriechroehre", [horizontal_cylinder(f, xs[0], xs[2], 2.1, 0.4, 0.35, segments=24)], keys=keys, object_type="Kriechroehre")

    ladder = [pipe_solid(f, (5.2 + dx, 0.75, 0.15), (5.2 + dx, 0.35, 2.7), 0.025, segments=6) for dx in (0.0, 0.5)]
    ladder += [pipe_solid(f, (5.2, 0.75 - 0.4 * k / 8, 0.15 + 2.55 * k / 8), (5.7, 0.75 - 0.4 * k / 8, 0.15 + 2.55 * k / 8), 0.018, segments=6) for k in range(1, 8)]
    ladder.append(box_solid(f, 5.0, 0.3, 0.0, 5.9, 1.0, 0.15))
    s.add("IfcBuildingElementProxy", "Endlosleiter", ladder, keys=keys, object_type="Endlosleiter")
    s.add(
        "IfcBuildingElementProxy",
        "Laufband",
        [box_solid(f, 5.0, 1.7, 0.0, 6.6, 2.35, 0.25), *(box_solid(f, 5.05, y, 0.25, 5.1, y + 0.05, 1.1) for y in (1.72, 2.28)), *(box_solid(f, 5.05, y, 1.05, 5.8, y + 0.05, 1.1) for y in (1.72, 2.28))],
        keys=keys,
        object_type="Laufband",
    )
    s.add("IfcBuildingElementProxy", "Nebelgenerator", [box_solid(f, 4.75, 2.95, 0.0, 5.2, 3.3, 0.45), pipe_solid(f, (4.75, 3.12, 0.35), (4.5, 3.12, 0.35), 0.05, segments=12)], keys=keys, object_type="Nebelgenerator")
    s.add("IfcController", "Leitstand", [box_solid(f, 5.4, 3.9, 0.0, 6.7, 4.6, 0.85), box_solid(f, 5.6, 4.35, 0.85, 6.5, 4.42, 1.35)], keys=keys)
    return s


def shooting_range() -> Scene:
    """Indoor range: three lanes with automatic target lifters behind a cover wall, steel bullet trap
    at the side wall, firing-line control panel and target cables."""
    s = corner_room("Schiessanlage", width=10.0, depth=4.0, height=3.0)
    f = s.ifc_file
    keys = (TARGET_SYSTEM,)
    s.add("IfcBuildingElementProxy", "Geschossfang", [profile_y(f, [(0.0, 0.0), (1.0, 0.0), (0.2, 2.6), (0.0, 2.6)], 0.15, 3.85)], object_type="Geschossfang")
    s.add("IfcWall", "Deckungswall", [box_solid(f, 1.95, 0.15, 0.0, 2.15, 3.85, 0.6)], predefined_type="PARAPET")

    lanes = (0.85, 2.0, 3.15)
    s.add("IfcActuator", "Scheibenzuganlagen", [box_solid(f, 1.4, y - 0.25, 0.0, 1.85, y + 0.25, 0.5) for y in lanes], keys=keys, predefined_type="ELECTRICACTUATOR")
    plates = []
    for i, y in enumerate(lanes):
        plates.append(pipe_solid(f, (1.62, y, 0.5), (1.62, y, 0.9) if i != 1 else (1.92, y, 0.55), 0.02, segments=8))
        plates.append(box_solid(f, 1.6, y - 0.3, 0.9, 1.64, y + 0.3, 1.9) if i != 1 else box_solid(f, 1.9, y - 0.3, 0.52, 2.9, y + 0.3, 0.56))
    s.add("IfcBuildingElementProxy", "Zielscheiben", plates, keys=keys, object_type="Zielscheibe")
    s.add("IfcFurniture", "Schuetzentische", [box_solid(f, 8.6, y - 0.4, 0.75, 9.3, y + 0.4, 0.8) for y in lanes], predefined_type="TABLE")
    s.add("IfcController", "Scheibensteuerung", [box_solid(f, 8.8, 0.0, 1.0, 9.4, 0.15, 1.6), box_solid(f, 8.9, 0.15, 1.2, 9.3, 0.17, 1.5)], keys=keys)
    for i, y in enumerate(lanes):
        _line(s, f"Steuerkabel-{i + 1}", [(9.1, 0.04, 1.0), (9.1, 0.04, 0.06 + i * 0.04), (1.63, 0.04, 0.06 + i * 0.04), (1.63, y - 0.25, 0.06 + i * 0.04)], 0.012, serves=keys, ifc_class="IfcCableSegment")
    return s


def gas_production() -> Scene:
    """Gas production room: feed compressor, two adsorber columns with controller, buffer tank,
    booster compressor and a cylinder filling ramp; gas detector on the back wall."""
    s = corner_room("Gasproduktion")
    f = s.ifc_file
    keys = (GAS_PRODUCTION,)
    s.add("IfcCompressor", "Zuluftkompressor", [box_solid(f, 0.1, 1.5, 0.0, 0.9, 2.4, 1.2)], predefined_type="ROTARY")
    s.add("IfcTank", "Adsorber", [vertical_cylinder_solid(f, x, 0.5, 0.0, 0.22, 1.9, segments=18) for x in (1.0, 1.6)], keys=keys, predefined_type="PRESSUREVESSEL", object_type="Adsorber")
    s.add("IfcController", "Generatorsteuerung", [box_solid(f, 2.0, 0.1, 0.3, 2.6, 0.5, 1.8)], keys=keys)
    s.add("IfcTank", "Puffertank", [vertical_cylinder_solid(f, 3.3, 0.6, 0.0, 0.4, 2.0, segments=24)], keys=keys, predefined_type="STORAGE")
    s.add("IfcCompressor", "Nachverdichter", [box_solid(f, 4.0, 0.2, 0.0, 4.8, 0.8, 1.0)], keys=keys, predefined_type="RECIPROCATING")
    cylinders = [vertical_cylinder_solid(f, x, y, 0.0, 0.11, 1.5, segments=14) for x in (5.15, 5.45, 5.75, 6.05) for y in (0.25, 0.55)]
    s.add("IfcTank", "Gasflaschen", cylinders, keys=keys, predefined_type="PRESSUREVESSEL", object_type="Gasflasche")
    s.add("IfcPipeSegment", "Fuellrampe", [pipe_solid(f, (5.0, 0.12, 1.75), (6.25, 0.12, 1.75), 0.03, segments=10)], keys=keys, predefined_type="RIGIDSEGMENT")
    for i, x in enumerate((5.15, 5.45, 5.75, 6.05)):
        _line(s, f"Fuellschlauch-{i + 1}", [(x, 0.12, 1.75), (x, 0.25, 1.6)], 0.012, keys=keys)
    _line(s, "Zuluft", [(0.5, 1.5, 1.2), (0.5, 1.5, 2.3), (0.5, 0.5, 2.3), (1.0, 0.5, 2.3), (1.0, 0.5, 1.9)], 0.035, serves=keys, segments=10)
    _line(s, "Produktgas", [(1.6, 0.5, 1.9), (1.6, 0.5, 2.4), (3.3, 0.5, 2.4), (3.3, 0.6, 2.0)], 0.03, serves=keys, segments=10)
    _line(s, "Hochdruckleitung", [(3.7, 0.6, 1.5), (4.4, 0.6, 1.5), (4.4, 0.5, 1.0)], 0.025, serves=keys, segments=10)
    _line(s, "Rampenleitung", [(4.7, 0.3, 1.0), (4.7, 0.3, 1.75), (5.0, 0.12, 1.75)], 0.025, serves=keys, segments=10)
    s.add("IfcSensor", "Gaswarnsensor", [box_solid(f, 2.9, 0.0, 2.3, 3.1, 0.1, 2.5)], keys=keys, predefined_type="GASSENSOR")
    return s


# ---------------------------------------------------------------------------
# Gebaeude: building maintenance unit
# ---------------------------------------------------------------------------

FACADE_BMU = "d12-06-005-fassadenreinigungsanlage"


def facade_maintenance() -> Scene:
    """Building with a roof-mounted maintenance unit: trolley on rails along the roof edge, jib over
    the facade and a cradle hanging on four ropes in front of the window bands."""
    s = Scene.new("Fassadenreinigung")
    f = s.ifc_file
    keys = (FACADE_BMU,)
    w, d, h, t = 8.0, 6.0, 9.0, 0.3
    _floor(s, -1.0, -1.0, w + 2.0, d + 3.0)
    _wall(s, "Fassade", (0.0, d - t, 0.0), w, h, t)
    _wall(s, "Seitenfassade", (w - t, 0.0, 0.0), d - t, h, t, direction=(0.0, 1.0))
    _wall(s, "Rueckwand", (0.0, 0.0, 0.0), w - t, h, t)
    _wall(s, "Seitenwand", (0.0, t, 0.0), d - 2 * t, h, t, direction=(0.0, 1.0))
    add_slab(f, name="Dach", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, 0.0, w, d), thickness=0.3, z_bottom=h, predefined_type="ROOF")
    zr = h + 0.3
    s.add("IfcBuildingElementProxy", "Fensterbaender", [box_solid(f, 0.4, d, z, w - 0.4, d + 0.03, z + 1.4) for z in (1.0, 4.0, 7.0)], object_type="Fensterband")

    s.add("IfcBuildingElementProxy", "Fahrschienen", [box_solid(f, 0.5, y - 0.06, zr, w - 0.5, y + 0.06, zr + 0.12) for y in (4.2, 5.0)], keys=keys, object_type="Fahrschiene")
    cx, cy = 3.8, 4.6
    s.add(
        "IfcTransportElement",
        "Dachwagen",
        [
            box_solid(f, cx - 0.8, cy - 0.6, zr + 0.12, cx + 0.8, cy + 0.6, zr + 1.0),
            vertical_cylinder_solid(f, cx, cy, zr + 1.0, 0.18, 1.0, segments=16),
            box_solid(f, cx - 0.12, cy - 1.0, zr + 2.0, cx + 0.12, d + 0.9, zr + 2.25),
            box_solid(f, cx - 0.6, d + 0.75, zr + 2.0, cx + 0.6, d + 0.95, zr + 2.25),
        ],
        keys=keys,
        predefined_type="LIFTINGGEAR",
    )
    cz0, cz1 = 4.3, 5.4
    s.add("IfcMember", "Seile", [pipe_solid(f, (x, d + 0.85, zr + 2.0), (x, d + 0.5, cz1), 0.012, segments=6) for x in (cx - 0.5, cx + 0.5)], keys=keys, predefined_type="USERDEFINED", object_type="Tragseil", thin=True)
    s.add(
        "IfcTransportElement",
        "Arbeitskorb",
        [
            box_solid(f, cx - 1.0, d + 0.15, cz0, cx + 1.0, d + 0.85, cz0 + 0.1),
            box_solid(f, cx - 1.0, d + 0.8, cz0 + 0.1, cx + 1.0, d + 0.85, cz1),
            box_solid(f, cx - 1.0, d + 0.15, cz1 - 0.05, cx + 1.0, d + 0.85, cz1),
            *(box_solid(f, x, d + 0.15, cz0 + 0.1, x + 0.05, d + 0.85, cz1) for x in (cx - 1.0, cx + 0.95)),
        ],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Arbeitskorb",
    )
    return s
