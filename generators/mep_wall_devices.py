"""MEP wall-device vignettes: Wandabschnitt Elektro and Wohnraum Aussenwand."""

from __future__ import annotations

from typing import Any

import ifcopenshell

from generators.base import create_project_shell, get_body_context
from generators.mep_parts import MepScene, box_solid, pipe_solid
from generators.parts import rect_polyline
from generators.slab import add_slab
from generators.wall import add_opening_filling, add_opening_in_wall, add_wall

# Metres. Devices sit on the +Y face of a wall along y = 0. The brand takes
# the top corner nearest the camera (the +X end), so devices stay left of it.
ELECTRO_WALL_LENGTH = 3.0
ELECTRO_WALL_THICKNESS = 0.12
ELECTRO_FLOOR_DEPTH = 1.1
HEATING_WALL_LENGTH = 3.6
HEATING_WALL_THICKNESS = 0.30
HEATING_SIDE_THICKNESS = 0.12
HEATING_FLOOR_DEPTH = 2.6
WALL_HEIGHT = 2.6
SLAB_THICKNESS = 0.20
DEVICE_PROTRUSION = 0.025

WALL_ELECTRO_SLUGS = frozenset(
    {
        "mep-switching-device",
        "mep-outlet",
        "mep-sensor",
        "mep-communications-appliance",
    }
)
WALL_HEATING_SLUGS = frozenset({"mep-space-heater", "mep-valve", "mep-gas-terminal"})


def _wall_box(
    f: ifcopenshell.file, x0: float, z0: float, width: float, height: float, depth: float = DEVICE_PROTRUSION
) -> ifcopenshell.entity_instance:
    """Device box on the +Y face of the y = 0 wall."""
    return box_solid(f, x0, 0.0, z0, x0 + width, depth, z0 + height)


def _scene(params: dict[str, Any], name: str) -> MepScene:
    ifc_file, _project, _site, _building, storey, body_context = create_project_shell(
        params.get("project_name") or name,
        storey_name="EG",
    )
    return MepScene(ifc_file, get_body_context(ifc_file) or body_context, storey)


def _add_framed_opening(
    scene: MepScene,
    *,
    host: ifcopenshell.entity_instance,
    name: str,
    wall_origin: tuple[float, float, float],
    wall_thickness: float,
    along: float,
    sill: float,
    width: float,
    height: float,
    ifc_class: str,
    predefined_type: str,
) -> None:
    opening = add_opening_in_wall(
        scene.ifc_file,
        host=host,
        name=f"{name}-Oeffnung",
        body_context=scene.body_context,
        along=along,
        sill=sill,
        clear_width=width,
        clear_height=height,
        wall_thickness=wall_thickness,
        wall_origin=wall_origin,
    )
    add_opening_filling(
        scene.ifc_file,
        opening=opening,
        name=name,
        body_context=scene.body_context,
        storey=scene.storey,
        along=along,
        sill=sill,
        clear_width=width,
        clear_height=height,
        wall_thickness=wall_thickness,
        wall_origin=wall_origin,
        ifc_class=ifc_class,
        predefined_type=predefined_type,
    )


def generate_mep_wall_electro(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Partition with a door; switch, sockets, thermostat and WLAN AP in one strip beside it."""
    params = dict(params or {})
    scene = _scene(params, "Wandabschnitt-Elektro")
    f = scene.ifc_file
    t = ELECTRO_WALL_THICKNESS

    add_slab(
        f,
        name="Bodenplatte",
        body_context=scene.body_context,
        storey=scene.storey,
        polyline=rect_polyline(0.0, -t, ELECTRO_WALL_LENGTH, ELECTRO_FLOOR_DEPTH),
        thickness=SLAB_THICKNESS,
        z_bottom=-SLAB_THICKNESS,
    )
    wall_origin = (0.0, -t, 0.0)
    wall = add_wall(
        f,
        name="Trennwand",
        body_context=scene.body_context,
        storey=scene.storey,
        origin=wall_origin,
        length=ELECTRO_WALL_LENGTH,
        height=WALL_HEIGHT,
        thickness=t,
        predefined_type="PARTITIONING",
    )
    door_along, door_width, door_height = 0.2, 0.9, 2.1
    _add_framed_opening(
        scene,
        host=wall,
        name="Innentuer",
        wall_origin=wall_origin,
        wall_thickness=t,
        along=door_along,
        sill=0.0,
        width=door_width,
        height=door_height,
        ifc_class="IfcDoor",
        predefined_type="DOOR",
    )

    strip_x = 1.28
    scene.device("mep-switching-device", [_wall_box(f, strip_x, 1.0, 0.1, 0.1)])
    for index in range(2):
        scene.device(
            "mep-outlet",
            [_wall_box(f, strip_x + index * 0.1, 0.25, 0.1, 0.1)],
        )
    sensor_z, sensor_h = 1.45, 0.13
    scene.device("mep-sensor", [_wall_box(f, strip_x, sensor_z, 0.1, sensor_h)])
    ap_size = 0.22
    scene.device(
        "mep-communications-appliance",
        [_wall_box(f, door_along + (door_width - ap_size) * 0.5, door_height + 0.12, ap_size, ap_size, depth=0.05)],
    )
    if params.get("system"):
        # Surface-mounted detector line straight up to the ceiling.
        x, y = strip_x + 0.05, 0.012
        cable = scene.context(
            "IfcCableSegment",
            "Melderlinie",
            [pipe_solid(f, (x, y, sensor_z + sensor_h), (x, y, WALL_HEIGHT), 0.012, segments=6)],
            predefined_type="CABLESEGMENT",
            serves=("mep-sensor",),
        )
        scene.thin.append(cable)
    return scene.finish(params)


def generate_mep_wall_heating(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Exterior wall with window and radiator; manifold cabinet; kitchen gas outlet."""
    params = dict(params or {})
    scene = _scene(params, "Wohnraum-Aussenwand")
    f = scene.ifc_file
    t = HEATING_WALL_THICKNESS
    ts = HEATING_SIDE_THICKNESS

    add_slab(
        f,
        name="Bodenplatte",
        body_context=scene.body_context,
        storey=scene.storey,
        polyline=rect_polyline(-ts, -t, HEATING_WALL_LENGTH, HEATING_FLOOR_DEPTH),
        thickness=SLAB_THICKNESS,
        z_bottom=-SLAB_THICKNESS,
    )
    wall_origin = (-ts, -t, 0.0)
    wall = add_wall(
        f,
        name="Aussenwand",
        body_context=scene.body_context,
        storey=scene.storey,
        origin=wall_origin,
        length=HEATING_WALL_LENGTH + ts,
        height=WALL_HEIGHT,
        thickness=t,
        predefined_type="SOLIDWALL",
    )
    _add_framed_opening(
        scene,
        host=wall,
        name="Fenster",
        wall_origin=wall_origin,
        wall_thickness=t,
        along=ts + 0.3,
        sill=0.9,
        width=1.2,
        height=1.3,
        ifc_class="IfcWindow",
        predefined_type="WINDOW",
    )
    add_wall(
        f,
        name="Seitenwand",
        body_context=scene.body_context,
        storey=scene.storey,
        origin=(0.0, 0.0, 0.0),
        length=HEATING_FLOOR_DEPTH,
        height=WALL_HEIGHT,
        thickness=ts,
        direction_xy=(0.0, 1.0),
        predefined_type="PARTITIONING",
    )

    scene.device("mep-space-heater", [box_solid(f, 0.35, 0.04, 0.15, 1.45, 0.14, 0.75)])

    # Underfloor-heating manifold cabinet on the side partition; loops drop into the screed.
    scene.device("mep-valve", [box_solid(f, 0.0, 1.4, 0.3, 0.12, 2.1, 1.0)])
    for y in (1.6, 1.9):
        scene.context(
            "IfcPipeSegment",
            "FBH-Kreis",
            [pipe_solid(f, (0.06, y, 0.0), (0.06, y, 0.3), 0.02)],
            serves=("mep-valve",),
        )

    scene.context(
        "IfcBuildingElementProxy",
        "Kuechenzeile",
        [box_solid(f, 2.1, 0.0, 0.0, 3.5, 0.62, 0.9)],
        predefined_type="USERDEFINED",
        object_type="Einbaumöbel",
    )
    scene.device("mep-gas-terminal", [box_solid(f, 2.7, 0.0, 0.95, 2.92, 0.07, 1.15)])
    if params.get("system"):
        scene.context(
            "IfcPipeSegment",
            "Gasleitung",
            [pipe_solid(f, (2.81, 0.03, 1.15), (2.81, 0.03, WALL_HEIGHT), 0.02)],
            serves=("mep-gas-terminal",),
        )
    return scene.finish(params)
