"""MEP plant room (Technikzentrale) and electrical room (Elektroraum) vignettes."""

from __future__ import annotations

from typing import Any

import ifcopenshell

from generators.base import create_project_shell, get_body_context
from generators.mep_parts import (
    MepScene,
    add_corner_room,
    box_solid,
    duct_solid,
    pipe_solid,
    vertical_cylinder_solid,
)

# Metres — open-corner room; devices stand along the back wall (y = 0) and
# the side wall (x = 0). The brand sits at the top right of the back wall,
# so pipes and trays stay below ~2.4 m there.
ROOM_WIDTH = 6.5
ROOM_DEPTH = 4.5
WALL_HEIGHT = 3.0
WALL_THICKNESS = 0.20
SLAB_THICKNESS = 0.25

_HEADER_Y = 0.22
_FLOW_Z = 2.15
_RETURN_Z = 2.35
_PIPE_R = 0.05

EQUIPMENT_SPACE_SLUG = "mep-schematic-equipment-space"
PLANT_ROOM_SLUGS = frozenset(
    {
        "mep-boiler",
        "mep-heat-exchanger",
        "mep-chiller",
        "mep-pump",
        "mep-compressor",
        "mep-gas-regulator",
        "mep-tank",
        EQUIPMENT_SPACE_SLUG,
    }
)
ELECTRICAL_ROOM_SLUGS = frozenset(
    {
        "mep-transformer",
        "mep-ups",
        "mep-electric-distribution-board",
        "mep-electric-generator",
    }
)


def _room_scene(params: dict[str, Any], storey_name: str) -> MepScene:
    ifc_file, _project, _site, _building, storey, body_context = create_project_shell(
        params.get("project_name") or "MEP",
        storey_name=storey_name,
    )
    body_context = get_body_context(ifc_file) or body_context
    add_corner_room(
        ifc_file,
        body_context=body_context,
        storey=storey,
        width=ROOM_WIDTH,
        depth=ROOM_DEPTH,
        wall_height=WALL_HEIGHT,
        wall_thickness=WALL_THICKNESS,
        slab_thickness=SLAB_THICKNESS,
    )
    return MepScene(ifc_file, body_context, storey)


def _header_stubs(
    scene: MepScene, name: str, x_flow: float, x_return: float, z_top: float
) -> None:
    """Flow / return stubs from a device top up to the header pair."""
    f = scene.ifc_file
    scene.context(
        "IfcPipeSegment",
        f"{name}-VL",
        [pipe_solid(f, (x_flow, _HEADER_Y, z_top), (x_flow, _HEADER_Y, _FLOW_Z), _PIPE_R)],
    )
    scene.context(
        "IfcPipeSegment",
        f"{name}-RL",
        [pipe_solid(f, (x_return, _HEADER_Y, z_top), (x_return, _HEADER_Y, _RETURN_Z), _PIPE_R)],
    )


def _add_plant_devices(scene: MepScene) -> None:
    f = scene.ifc_file

    # Header pair along the back wall; enters through the side wall (district heating).
    for name, z in (("Verteiler-VL", _FLOW_Z), ("Verteiler-RL", _RETURN_Z)):
        scene.context(
            "IfcPipeSegment",
            name,
            [pipe_solid(f, (-WALL_THICKNESS, _HEADER_Y, z), (ROOM_WIDTH - 0.2, _HEADER_Y, z), _PIPE_R)],
        )

    scene.device("mep-heat-exchanger", [box_solid(f, 0.3, 0.0, 0.5, 1.3, 0.45, 1.9)])
    _header_stubs(scene, "FWS", 0.6, 1.0, 1.9)

    scene.device(
        "mep-boiler",
        [
            vertical_cylinder_solid(f, 2.1, 0.5, 0.0, 0.40, 1.80),
            vertical_cylinder_solid(f, 2.1, 0.5, 1.80, 0.10, WALL_HEIGHT - 1.80, segments=8),
        ],
    )
    _header_stubs(scene, "WE", 1.85, 2.35, 1.80)

    scene.context(
        "IfcPipeSegment",
        "Pumpenstrang",
        [pipe_solid(f, (3.0, _HEADER_Y, 0.0), (3.0, _HEADER_Y, _FLOW_Z), _PIPE_R)],
    )
    # In-line pump above the chiller top so it is not hidden behind it.
    scene.device(
        "mep-pump",
        [
            box_solid(f, 2.80, 0.03, 1.56, 3.20, 0.43, 1.92),
            pipe_solid(f, (3.0, 0.43, 1.74), (3.0, 0.72, 1.74), 0.12, segments=10),
        ],
    )

    scene.device("mep-chiller", [box_solid(f, 3.6, 0.1, 0.0, 6.1, 1.1, 1.6)])
    _header_stubs(scene, "KM", 4.1, 5.6, 1.60)

    # Compressed air: compressor + standing air receiver along the side wall.
    scene.device("mep-compressor", [box_solid(f, 0.2, 1.3, 0.0, 1.0, 2.0, 1.0)])
    scene.context(
        "IfcTank",
        "Druckluftbehaelter",
        [vertical_cylinder_solid(f, 0.6, 2.6, 0.0, 0.30, 1.40)],
        predefined_type="PRESSUREVESSEL",
    )
    scene.context(
        "IfcPipeSegment",
        "Druckluft",
        [pipe_solid(f, (0.6, 2.0, 0.7), (0.6, 2.3, 0.7), 0.03)],
    )

    # Gas line rises from the floor to the wall-mounted pressure regulator.
    scene.context(
        "IfcPipeSegment",
        "Gas-Zuleitung",
        [pipe_solid(f, (0.15, 3.6, 0.0), (0.15, 3.6, 0.95), 0.035)],
    )
    scene.device("mep-gas-regulator", [box_solid(f, 0.0, 3.35, 0.95, 0.30, 3.85, 1.45)])
    scene.context(
        "IfcPipeSegment",
        "Gas-Verteilung",
        [pipe_solid(f, (0.15, 3.6, 1.45), (0.15, 3.6, 2.6), 0.035)],
    )

    # Storage tank standing on the floor, with two manhole covers on top.
    tank_top = 0.90
    scene.device(
        "mep-tank",
        [
            box_solid(f, 3.2, 2.6, 0.0, 4.8, 3.6, tank_top),
            vertical_cylinder_solid(f, 3.6, 3.1, tank_top, 0.25, 0.08),
            vertical_cylinder_solid(f, 4.4, 3.1, tank_top, 0.25, 0.08),
        ],
    )


def generate_mep_plant_room(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Technikzentrale Wärme/Kälte; the Erzeugerplatz card shows the empty room + volume."""
    params = dict(params or {})
    scene = _room_scene(params, "UG")
    if params.get("highlight") == EQUIPMENT_SPACE_SLUG:
        scene.device(
            EQUIPMENT_SPACE_SLUG,
            [box_solid(scene.ifc_file, 0.0, 0.0, 0.0, ROOM_WIDTH, 3.4, 2.6)],
        )
    else:
        _add_plant_devices(scene)
    return scene.finish(params)


def generate_mep_electrical_room(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Elektroraum: switchboard, UPS, transformer and backup generator."""
    params = dict(params or {})
    scene = _room_scene(params, "UG")
    f = scene.ifc_file

    tray_z = 2.35
    scene.context(
        "IfcCableCarrierSegment",
        "Trasse-Rueckwand",
        [duct_solid(f, (-WALL_THICKNESS, 0.35, tray_z), (ROOM_WIDTH - 0.2, 0.35, tray_z), 0.40, 0.08)],
    )
    for name, x, z_top in (("Trasse-HV", 1.2, 2.1), ("Trasse-USV", 3.5, 2.0)):
        scene.context(
            "IfcCableCarrierSegment",
            name,
            [duct_solid(f, (x, 0.30, z_top), (x, 0.30, tray_z - 0.04), 0.30, 0.08)],
        )

    scene.device(
        "mep-electric-distribution-board",
        [box_solid(f, x0, 0.0, 0.0, x0 + 0.6, 0.6, 2.1) for x0 in (0.3, 0.9, 1.5)],
    )
    scene.device(
        "mep-ups",
        [box_solid(f, x0, 0.0, 0.0, x0 + 0.6, 0.8, 2.0) for x0 in (2.6, 3.2, 3.8)],
    )

    transformer = [box_solid(f, 0.3, 1.6, 0.0, 1.5, 3.4, 1.6)]
    transformer += [
        box_solid(f, 1.5, y, 0.3, 1.75, y + 0.05, 1.4) for y in (1.85, 2.15, 2.45, 2.75, 3.05)
    ]
    transformer += [
        vertical_cylinder_solid(f, 0.9, y, 1.6, 0.06, 0.25, segments=8) for y in (2.0, 2.5, 3.0)
    ]
    scene.device("mep-transformer", transformer)

    scene.context(
        "IfcBuildingElementProxy",
        "Fundamentsockel",
        [box_solid(f, 3.0, 2.2, 0.0, 6.2, 3.6, 0.15)],
        predefined_type="USERDEFINED",
        object_type="Sockel",
    )
    scene.device(
        "mep-electric-generator",
        [
            box_solid(f, 3.2, 2.4, 0.15, 5.6, 3.4, 1.5),
            box_solid(f, 5.6, 2.35, 0.15, 6.0, 3.45, 1.7),
            vertical_cylinder_solid(f, 4.0, 2.9, 1.5, 0.10, WALL_HEIGHT - 1.5, segments=8),
        ],
    )
    return scene.finish(params)
