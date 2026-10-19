"""Building vignettes: corridor, wall strip, kitchen, office ceiling, roof, hall, site."""

from __future__ import annotations

import math

from generators.covering import add_covering
from generators.mep_parts import box_solid, duct_solid, pipe_solid, vertical_cylinder_solid
from generators.parts import rect_polyline
from generators.roofing import DEFAULT_SLAB_THICKNESS, generate_roofing
from generators.slab import add_slab
from generators.wall import add_opening_filling, add_opening_in_wall, add_wall

from dataschema.geometry import frustum, tilted_panel
from dataschema.scene import Scene
from dataschema.scenes_rooms import corner_room, horizontal_cylinder


def framed_opening(
    s: Scene,
    host,
    name: str,
    *,
    wall_origin: tuple[float, float, float],
    wall_thickness: float,
    along: float,
    sill: float,
    width: float,
    height: float,
    ifc_class: str = "IfcDoor",
    predefined_type: str = "DOOR",
    direction_xy: tuple[float, float] = (1.0, 0.0),
):
    opening = add_opening_in_wall(
        s.ifc_file,
        host=host,
        name=f"{name}-Oeffnung",
        body_context=s.body_context,
        along=along,
        sill=sill,
        clear_width=width,
        clear_height=height,
        wall_thickness=wall_thickness,
        wall_origin=wall_origin,
        direction_xy=direction_xy,
    )
    return add_opening_filling(
        s.ifc_file,
        opening=opening,
        name=name,
        body_context=s.body_context,
        storey=s.storey,
        along=along,
        sill=sill,
        clear_width=width,
        clear_height=height,
        wall_thickness=wall_thickness,
        wall_origin=wall_origin,
        direction_xy=direction_xy,
        ifc_class=ifc_class,
        predefined_type=predefined_type,
    )


def _floor(s: Scene, x0: float, y0: float, x1: float, y1: float, thickness: float = 0.25) -> None:
    add_slab(
        s.ifc_file,
        name="Bodenplatte",
        body_context=s.body_context,
        storey=s.storey,
        polyline=rect_polyline(x0, y0, x1, y1),
        thickness=thickness,
        z_bottom=-thickness,
    )


def _wall(s: Scene, name: str, origin, length: float, height: float, thickness: float, direction=(1.0, 0.0), predefined="SOLIDWALL"):
    return add_wall(
        s.ifc_file,
        name=name,
        body_context=s.body_context,
        storey=s.storey,
        origin=origin,
        length=length,
        height=height,
        thickness=thickness,
        direction_xy=direction,
        predefined_type=predefined,
    )


# ---------------------------------------------------------------------------
# Korridor: safety and security devices
# ---------------------------------------------------------------------------

CORRIDOR_LENGTH = 9.0
CORRIDOR_WIDTH = 2.4
CORRIDOR_HEIGHT = 3.0


def corridor() -> Scene:
    """Corridor with two doors, turnstiles, fire curtain and the security device families."""
    s = Scene.new("Korridor")
    f = s.ifc_file
    t = 0.2
    _floor(s, -t, -t, CORRIDOR_LENGTH, CORRIDOR_WIDTH)
    origin = (-t, -t, 0.0)
    back = _wall(s, "Rueckwand", origin, CORRIDOR_LENGTH + t, CORRIDOR_HEIGHT, t)
    _wall(s, "Seitenwand", (0.0, 0.0, 0.0), CORRIDOR_WIDTH, CORRIDOR_HEIGHT, t, direction=(0.0, 1.0))

    door_1 = framed_opening(s, back, "Brandschutztuer", wall_origin=origin, wall_thickness=t, along=1.2, sill=0.0, width=1.0, height=2.1)
    s.tag(door_1, ("i-014-abschlusse",))
    door_2 = framed_opening(s, back, "Zutrittstuer", wall_origin=origin, wall_thickness=t, along=5.2, sill=0.0, width=1.0, height=2.1)
    s.tag(door_2, ("i-079-el-zutrittskontrolle",))

    # Fire curtain housing under the slab plus guide rails on both walls.
    s.add(
        "IfcBuildingElementProxy",
        "Brandschutzvorhang",
        [box_solid(f, 3.6, 0.0, 2.65, 3.9, CORRIDOR_WIDTH, 2.95), box_solid(f, 3.65, 0.0, 0.0, 3.85, 0.06, 2.65)],
        keys=("i-014-abschlusse",),
        object_type="Brandschutzvorhang",
    )

    def wall_box(x0: float, z0: float, w: float, h: float, d: float = 0.06):
        return box_solid(f, x0, 0.0, z0, x0 + w, d, z0 + h)

    # Emergency lighting: exit signs above both doors + emergency luminaires.
    s.add(
        "IfcLightFixture",
        "Fluchtwegkennzeichnung",
        [wall_box(1.45, 2.2, 0.5, 0.2, 0.08), wall_box(5.45, 2.2, 0.5, 0.2, 0.08)],
        keys=("i-002-notlichtanlage",),
        predefined_type="SECURITYLIGHTING",
    )
    s.add(
        "IfcLightFixture",
        "Notleuchte",
        [wall_box(3.0, 2.55, 0.35, 0.12, 0.1), box_solid(f, 0.0, 1.6, 2.55, 0.1, 1.95, 2.67)],
        keys=("i-002-notlichtanlage",),
        predefined_type="SECURITYLIGHTING",
    )
    # Video cameras on brackets.
    s.add(
        "IfcAudioVisualAppliance",
        "Kamera",
        [
            box_solid(f, 4.55, 0.0, 2.45, 4.65, 0.25, 2.55),
            pipe_solid(f, (4.6, 0.2, 2.42), (4.6, 0.45, 2.3), 0.08, segments=10),
            box_solid(f, 0.0, 0.35, 2.45, 0.25, 0.45, 2.55),
            pipe_solid(f, (0.2, 0.4, 2.42), (0.45, 0.4, 2.3), 0.08, segments=10),
        ],
        keys=("i-010-videouberwachung",),
        predefined_type="CAMERA",
    )
    # Evacuation speakers.
    s.add(
        "IfcAudioVisualAppliance",
        "Lautsprecher",
        [wall_box(2.6, 2.0, 0.25, 0.25, 0.1), wall_box(6.8, 2.0, 0.25, 0.25, 0.1)],
        keys=("i-025-evakuationsanlage",),
        predefined_type="SPEAKER",
    )
    # Card reader beside the access door.
    s.add("IfcSensor", "Kartenleser", [wall_box(6.35, 1.05, 0.09, 0.14, 0.04)], keys=("i-079-el-zutrittskontrolle",), predefined_type="IDENTIFIERSENSOR")
    # Alarm panel and flashing beacon on the side wall.
    s.add("IfcController", "Alarmzentrale", [box_solid(f, 0.0, 1.0, 1.1, 0.12, 1.5, 1.8)], keys=("i-012-alarmmanagement",))
    s.add("IfcAlarm", "Blitzleuchte", [vertical_cylinder_solid(f, 0.08, 1.25, 2.1, 0.07, 0.15, segments=12)], keys=("i-012-alarmmanagement",), predefined_type="LIGHT")
    # Turnstiles across the corridor end.
    turnstiles = []
    for y in (0.15, 0.95, 1.75):
        turnstiles.append(box_solid(f, 7.6, y, 0.0, 8.6, y + 0.22, 1.0))
        turnstiles.append(box_solid(f, 8.0, y + 0.22, 0.85, 8.05, y + 0.62, 0.9))
    s.add("IfcBuildingElementProxy", "Drehsperren", turnstiles, keys=("i-009-personenvereinzelungsanlage",), object_type="Personenvereinzelung")
    return s


# ---------------------------------------------------------------------------
# Wandabschnitt Elektro: home automation and junction box
# ---------------------------------------------------------------------------

def electro_wall() -> Scene:
    """Partition with door; switch, sockets, room controller, presence sensor, junction box."""
    s = Scene.new("Wandabschnitt-Elektro")
    f = s.ifc_file
    t, length, height = 0.12, 3.0, 2.6
    _floor(s, 0.0, -t, length, 1.1, thickness=0.2)
    origin = (0.0, -t, 0.0)
    wall = _wall(s, "Trennwand", origin, length, height, t, predefined="PARTITIONING")
    framed_opening(s, wall, "Innentuer", wall_origin=origin, wall_thickness=t, along=0.2, sill=0.0, width=0.9, height=2.1)

    def dev(x0: float, z0: float, w: float, h: float, d: float = 0.025):
        return box_solid(f, x0, 0.0, z0, x0 + w, d, z0 + h)

    x = 1.28
    s.add("IfcSwitchingDevice", "Taster", [dev(x, 1.0, 0.1, 0.1)], keys=("i-080-domotik",), predefined_type="MOMENTARYSWITCH")
    s.add("IfcOutlet", "Steckdosen", [dev(x, 0.25, 0.1, 0.1), dev(x + 0.1, 0.25, 0.1, 0.1)], predefined_type="POWEROUTLET")
    s.add("IfcController", "Raumcontroller", [dev(x - 0.02, 1.35, 0.14, 0.2, 0.03)], keys=("i-080-domotik",), predefined_type="PROGRAMMABLE")
    s.add("IfcSensor", "Praesenzmelder", [dev(x - 0.02, 2.15, 0.14, 0.14, 0.05)], keys=("i-080-domotik",), predefined_type="MOVEMENTSENSOR")
    s.add("IfcActuator", "Storenantrieb", [dev(0.3, 2.3, 0.18, 0.12, 0.05)], keys=("i-080-domotik",), predefined_type="ELECTRICACTUATOR")
    s.add("IfcJunctionBox", "Abzweigdose", [dev(0.85, 2.3, 0.12, 0.12, 0.04)], keys=("abzweigdose",), predefined_type="POWER")
    return s


# ---------------------------------------------------------------------------
# Kueche: electrical appliances and a fluid terminal
# ---------------------------------------------------------------------------

def kitchen() -> Scene:
    """Kitchen wall with window, counter, fridge, oven, dishwasher, hob and gas outlet."""
    s = Scene.new("Kueche")
    f = s.ifc_file
    t, ts, length, depth, height = 0.3, 0.12, 3.6, 2.6, 2.6
    _floor(s, -ts, -t, length, depth, thickness=0.2)
    origin = (-ts, -t, 0.0)
    wall = _wall(s, "Aussenwand", origin, length + ts, height, t)
    framed_opening(s, wall, "Fenster", wall_origin=origin, wall_thickness=t, along=ts + 1.6, sill=1.1, width=1.0, height=1.1, ifc_class="IfcWindow", predefined_type="WINDOW")
    _wall(s, "Seitenwand", (0.0, 0.0, 0.0), depth, height, ts, direction=(0.0, 1.0), predefined="PARTITIONING")

    s.add("IfcFurniture", "Kuechenzeile", [box_solid(f, 0.65, 0.0, 0.0, 3.5, 0.62, 0.9)], predefined_type="USERDEFINED", object_type="Einbaumöbel")
    s.add(
        "IfcElectricAppliance",
        "Haushaltgeraete",
        [
            box_solid(f, 0.0, 0.0, 0.0, 0.62, 0.65, 1.95),
            box_solid(f, 0.75, 0.62, 0.1, 1.35, 0.66, 0.72),
            box_solid(f, 2.85, 0.62, 0.1, 3.45, 0.66, 0.72),
            box_solid(f, 0.8, 0.05, 0.9, 1.3, 0.55, 0.93),
        ],
        keys=("elektrisches-gerat",),
        predefined_type="REFRIGERATOR",
    )
    s.add("IfcFlowTerminal", "Gasanschluss", [box_solid(f, 2.2, 0.0, 0.95, 2.42, 0.07, 1.15)], keys=("endgerat-fluid",))
    return s


# ---------------------------------------------------------------------------
# Buero mit Abhangdecke: lamps and light distribution
# ---------------------------------------------------------------------------

def office_lighting() -> Scene:
    """Dotted suspended ceiling with recessed luminaires; lamps and light cones below."""
    s = corner_room("Buero-Licht", width=5.0, depth=4.0)
    f = s.ifc_file
    ceiling_bottom = 2.62
    ceiling = add_covering(
        f,
        name="Abhangdecke",
        body_context=s.body_context,
        storey=s.storey,
        polyline=rect_polyline(0.0, 0.0, 5.0, 4.0),
        thickness=0.04,
        z_bottom=ceiling_bottom,
        predefined_type="CEILING",
    )
    s.dotted.append(ceiling)
    s.add("IfcFurniture", "Tisch", [box_solid(f, 1.2, 1.4, 0.7, 3.4, 2.4, 0.75)], predefined_type="TABLE")
    for x in (1.4, 3.2):
        s.add("IfcBuildingElementProxy", f"Tischbein-{x}", [box_solid(f, x - 0.03, 1.45, 0.0, x + 0.03, 2.35, 0.7)], object_type="Tischbein")

    for cx, cy in ((1.6, 1.9), (3.4, 1.9)):
        s.add("IfcLightFixture", f"Leuchte-{cx}", [box_solid(f, cx - 0.6, cy - 0.15, ceiling_bottom - 0.04, cx + 0.6, cy + 0.15, ceiling_bottom + 0.1)], predefined_type="DIRECTIONSOURCE")
        s.add(
            "IfcLamp",
            f"Lampe-{cx}",
            [horizontal_cylinder(f, cx - 0.55, cx + 0.55, cy + dy, ceiling_bottom - 0.08, 0.025, segments=10) for dy in (-0.07, 0.07)],
            keys=("lampe",),
            predefined_type="FLUORESCENT",
        )
        s.add(
            "IfcBuildingElementProxy",
            f"Lichtkegel-{cx}",
            [frustum(f, cx, cy, ceiling_bottom - 0.1, 0.76, (0.55, 0.12), (0.95, 0.6))],
            keys=("lichtquelle",),
            object_type="Lichtquelle",
        )
    s.volume("lichtquelle")
    return s


# ---------------------------------------------------------------------------
# Dach: PV, solar thermal, flue terminal
# ---------------------------------------------------------------------------

ROOF_WIDTH = 7.0
ROOF_DEPTH = 5.0


def roof_energy() -> Scene:
    """Flat roof with PV rows and inverter, solar collectors with storage, chimney with flue terminal."""
    ifc_file, _roofing = generate_roofing({"project_name": "Dach-Energie", "slab_width": ROOF_WIDTH, "slab_depth": ROOF_DEPTH})
    s = Scene.wrap(ifc_file)
    f = ifc_file
    z0 = DEFAULT_SLAB_THICKNESS + 0.36

    # PV: three south-facing rows (left half, seen from the camera).
    for i, y in enumerate((1.4, 2.6, 3.8)):
        s.add("IfcBuildingElementProxy", f"Ballast-PV-{i}", [box_solid(f, 3.8, y - 0.9, DEFAULT_SLAB_THICKNESS, 6.6, y - 0.75, z0)], object_type="Unterkonstruktion")
        s.add(
            "IfcSolarDevice",
            f"PV-Reihe-{i + 1}",
            [tilted_panel(f, 3.8, 6.6, y, 0.9, z0, 0.35)],
            keys=("solargerat", "i-037-photovoltaikanlage"),
            predefined_type="SOLARPANEL",
        )
    s.add("IfcElectricFlowStorageDevice", "Wechselrichter", [box_solid(f, 6.2, 4.2, z0, 6.7, 4.5, z0 + 0.6)], keys=("i-037-photovoltaikanlage",), object_type="Wechselrichter")
    # Solar thermal: two steeper collectors and a small storage tank.
    for i, y in enumerate((1.6, 3.0)):
        s.add("IfcBuildingElementProxy", f"Ballast-ST-{i}", [box_solid(f, 0.6, y - 1.0, DEFAULT_SLAB_THICKNESS, 2.6, y - 0.85, z0)], object_type="Unterkonstruktion")
        s.add(
            "IfcSolarDevice",
            f"Kollektor-{i + 1}",
            [tilted_panel(f, 0.6, 2.6, y, 0.9, z0, 0.7, thickness=0.09)],
            keys=("i-074-warmeerz-solar",),
            predefined_type="SOLARCOLLECTOR",
        )
    s.add("IfcPipeSegment", "Solarleitung", [pipe_solid(f, (2.6, 2.6, z0 + 0.2), (2.6, 4.2, z0 + 0.2), 0.03)])
    s.add("IfcTank", "Solarspeicher", [horizontal_cylinder(f, 0.6, 2.4, 4.3, z0 + 0.3, 0.3, segments=16)], keys=("i-074-warmeerz-solar",), predefined_type="STORAGE")
    # Chimney with flue terminal.
    s.add("IfcChimney", "Kamin", [box_solid(f, 3.05, 0.4, DEFAULT_SLAB_THICKNESS, 3.45, 0.8, 1.6)])
    s.add(
        "IfcStackTerminal",
        "Abgasterminal",
        [vertical_cylinder_solid(f, 3.25, 0.6, 1.6, 0.13, 0.35, segments=12), vertical_cylinder_solid(f, 3.25, 0.6, 1.95, 0.24, 0.05, segments=12)],
        keys=("dach-abgasterminal",),
        predefined_type="COWL",
    )
    return s


# ---------------------------------------------------------------------------
# Halle: crane runway and track
# ---------------------------------------------------------------------------

def hall() -> Scene:
    """Industrial hall corner with an overhead crane on runways and a rail track through the gate."""
    s = corner_room("Halle", width=12.0, depth=8.0, height=6.5)
    f = s.ifc_file
    crane = ("i-003-krananlagen",)
    for x in (2.0, 6.0, 10.0):
        s.add("IfcColumn", f"Stuetze-{x}", [box_solid(f, x - 0.15, 7.2, 0.0, x + 0.15, 7.5, 6.5)], predefined_type="COLUMN")
        s.add("IfcBuildingElementProxy", f"Konsole-{x}", [box_solid(f, x - 0.15, 7.0, 4.6, x + 0.15, 7.2, 4.9)], keys=crane, object_type="Kranbahnkonsole")
        s.add("IfcBuildingElementProxy", f"Wandkonsole-{x}", [box_solid(f, x - 0.15, 0.0, 4.6, x + 0.15, 0.4, 4.9)], keys=crane, object_type="Kranbahnkonsole")
    s.add("IfcBeam", "Kranbahn-1", [box_solid(f, 0.0, 0.15, 4.9, 12.0, 0.4, 5.3)], keys=crane, predefined_type="USERDEFINED", object_type="Kranbahntraeger")
    s.add("IfcBeam", "Kranbahn-2", [box_solid(f, 0.0, 7.0, 4.9, 12.0, 7.25, 5.3)], keys=crane, predefined_type="USERDEFINED", object_type="Kranbahntraeger")
    s.add("IfcBeam", "Kranbruecke", [box_solid(f, 5.0, 0.15, 5.3, 5.5, 7.25, 5.9), box_solid(f, 5.9, 0.15, 5.3, 6.4, 7.25, 5.9)], keys=crane, predefined_type="USERDEFINED", object_type="Kranbruecke")
    s.add("IfcBuildingElementProxy", "Laufkatze", [box_solid(f, 4.9, 3.4, 5.9, 6.5, 4.3, 6.3), pipe_solid(f, (5.7, 3.85, 5.3), (5.7, 3.85, 3.4), 0.03, segments=6)], keys=crane, object_type="Laufkatze")
    s.add("IfcBuildingElementProxy", "Lasthaken", [box_solid(f, 5.55, 3.7, 3.1, 5.85, 4.0, 3.4)], keys=crane, object_type="Lasthaken")

    # Track along X: sleepers + two rails.
    track = ("i-028-gleisanlagen",)
    for i in range(16):
        x = 0.4 + i * 0.75
        s.add("IfcBuildingElementProxy", f"Schwelle-{i}", [box_solid(f, x, 3.0, -0.0, x + 0.25, 5.6, 0.12)], keys=track, object_type="Schwelle")
    for y in (3.55, 5.05):
        s.add("IfcBuildingElementProxy", f"Schiene-{y}", [box_solid(f, 0.0, y - 0.04, 0.12, 12.0, y + 0.04, 0.27)], keys=track, object_type="Schiene")
    s.add("IfcBuildingElementProxy", "Gueterwagen", [box_solid(f, 7.5, 3.2, 0.6, 11.5, 5.4, 2.8)], object_type="Gueterwagen")
    return s


# ---------------------------------------------------------------------------
# Gelaende: wind and hydro power
# ---------------------------------------------------------------------------

def site_power() -> Scene:
    """Terrain with a farm building, a wind turbine and a small hydro plant on a channel."""
    s = Scene.new("Gelaende", storey_name="Terrain")
    f = s.ifc_file
    add_slab(f, name="Terrain", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, 0.0, 40.0, 26.0), thickness=0.4, z_bottom=-0.4, predefined_type="BASESLAB")
    s.add("IfcBuildingElementProxy", "Gebaeude", [box_solid(f, 3.0, 3.0, 0.0, 13.0, 10.0, 6.0)], object_type="Gebaeude")

    wind = ("i-068-windkraftwerke",)
    tx, ty = 30.0, 7.0
    s.add("IfcBuildingElementProxy", "Turm", [vertical_cylinder_solid(f, tx, ty, 0.0, 1.0, 24.0, segments=16)], keys=wind, object_type="Turm")
    s.add("IfcBuildingElementProxy", "Gondel", [box_solid(f, tx - 1.0, ty - 3.0, 24.0, tx + 1.0, ty + 1.5, 26.0)], keys=wind, object_type="Gondel")
    hub = (tx, ty + 1.8, 25.0)
    s.add("IfcBuildingElementProxy", "Nabe", [pipe_solid(f, (tx, ty + 1.5, 25.0), hub, 0.8, segments=12)], keys=wind, object_type="Nabe")
    blades = []
    for angle in (90.0, 210.0, 330.0):
        a = math.radians(angle)
        dx, dz = math.cos(a), math.sin(a)
        blades.append(duct_solid(f, (hub[0] + 0.6 * dx, hub[1], hub[2] + 0.6 * dz), (hub[0] + 11.0 * dx, hub[1], hub[2] + 11.0 * dz), 0.9, 0.25))
    s.add("IfcBuildingElementProxy", "Rotorblaetter", blades, keys=wind, object_type="Rotorblatt")

    # Small hydro: channel cut, weir, penstock down to a turbine house.
    hydro = ("i-067-wasserkraftwerke",)
    s.add("IfcBuildingElementProxy", "Kanal-Ufer-1", [box_solid(f, 0.0, 17.0, 0.0, 40.0, 17.6, 0.8)], object_type="Ufermauer")
    s.add("IfcBuildingElementProxy", "Kanal-Ufer-2", [box_solid(f, 0.0, 21.4, 0.0, 40.0, 22.0, 0.8)], object_type="Ufermauer")
    s.add("IfcBuildingElementProxy", "Wehr", [box_solid(f, 14.0, 17.6, 0.0, 15.0, 21.4, 1.6)], keys=hydro, object_type="Wehr")
    s.add("IfcPipeSegment", "Druckleitung", [pipe_solid(f, (15.0, 19.5, 1.0), (22.0, 19.5, 0.6), 0.5, segments=14)], keys=hydro, predefined_type="RIGIDSEGMENT")
    s.add("IfcBuildingElementProxy", "Turbinenhaus", [box_solid(f, 22.0, 18.0, 0.0, 27.0, 21.0, 4.0)], keys=hydro, object_type="Turbinenhaus")
    return s
