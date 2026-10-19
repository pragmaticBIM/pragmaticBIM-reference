"""MEP office ceiling (Büro mit Abhangdecke) — ceiling devices + plenum duct."""

from __future__ import annotations

from typing import Any

import ifcopenshell

from generators.base import create_project_shell, get_body_context
from generators.covering import add_covering
from generators.mep_parts import (
    MepScene,
    add_corner_room,
    box_solid,
    duct_solid,
    vertical_cylinder_solid,
)
from generators.parts import rect_polyline

# Metres — the suspended ceiling is drawn dotted (no faces) so devices set into
# it and the supply duct in the plenum above read from the isometric camera.
ROOM_WIDTH = 5.0
ROOM_DEPTH = 4.0
WALL_HEIGHT = 3.0
WALL_THICKNESS = 0.20
CEILING_BOTTOM = 2.62
CEILING_THICKNESS = 0.04

_DUCT_Y = 0.6
_DUCT_Z = 2.85
_DUCT_W = 0.40
_DUCT_H = 0.25
_BRANCH_X = 4.3
_BRANCH_W = 0.30
_BRANCH_H = 0.20

OFFICE_CEILING_SLUGS = frozenset(
    {
        "mep-air-terminal",
        "mep-light-fixture",
        "mep-alarm",
        "mep-fire-suppression-terminal",
        "mep-cooled-beam",
        "mep-air-terminal-box",
        "mep-damper",
        "mep-actuator",
    }
)


def generate_mep_office_ceiling(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Office with dotted suspended ceiling, ceiling terminals and a VAV supply run."""
    params = dict(params or {})
    ifc_file, _project, _site, _building, storey, body_context = create_project_shell(
        params.get("project_name") or "Buero-Decke",
        storey_name="1.OG",
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
    )
    scene = MepScene(ifc_file, body_context, storey)
    f = ifc_file

    ceiling = add_covering(
        f,
        name="Abhangdecke",
        body_context=body_context,
        storey=storey,
        polyline=rect_polyline(0.0, 0.0, ROOM_WIDTH, ROOM_DEPTH),
        thickness=CEILING_THICKNESS,
        z_bottom=CEILING_BOTTOM,
        predefined_type="CEILING",
    )
    scene.dotted.append(ceiling)
    z_ceiling_top = CEILING_BOTTOM + CEILING_THICKNESS

    # Supply duct enters through the side wall: fire damper in the wall, VAV box, branch.
    half_w, half_h = _DUCT_W * 0.5, _DUCT_H * 0.5
    scene.device(
        "mep-damper",
        [box_solid(f, -0.15, _DUCT_Y - half_w - 0.03, _DUCT_Z - half_h - 0.03, 0.25, _DUCT_Y + half_w + 0.03, _DUCT_Z + half_h + 0.03)],
    )
    scene.device(
        "mep-actuator",
        [box_solid(f, 0.0, _DUCT_Y + half_w + 0.03, _DUCT_Z - 0.12, 0.26, _DUCT_Y + half_w + 0.20, _DUCT_Z + 0.12)],
    )
    scene.context(
        "IfcDuctSegment",
        "Zuluft-1",
        [duct_solid(f, (0.25, _DUCT_Y, _DUCT_Z), (2.2, _DUCT_Y, _DUCT_Z), _DUCT_W, _DUCT_H)],
    )
    scene.device(
        "mep-air-terminal-box",
        [box_solid(f, 2.2, _DUCT_Y - 0.27, _DUCT_Z - 0.15, 3.0, _DUCT_Y + 0.27, _DUCT_Z + 0.15)],
    )
    scene.context(
        "IfcDuctSegment",
        "Zuluft-2",
        [duct_solid(f, (3.0, _DUCT_Y, _DUCT_Z), (_BRANCH_X + _BRANCH_W * 0.5, _DUCT_Y, _DUCT_Z), _DUCT_W, _DUCT_H)],
    )
    scene.context(
        "IfcDuctSegment",
        "Zuluft-Abzweig",
        [duct_solid(f, (_BRANCH_X, _DUCT_Y + half_w, _DUCT_Z), (_BRANCH_X, 2.8, _DUCT_Z), _BRANCH_W, _BRANCH_H)],
    )

    # Ceiling terminals: tops sit just above the ceiling plane so they read from above.
    for y0 in (1.0, 2.2):
        scene.device(
            "mep-air-terminal",
            [box_solid(f, _BRANCH_X - 0.3, y0, CEILING_BOTTOM - 0.05, _BRANCH_X + 0.3, y0 + 0.6, z_ceiling_top + 0.02)],
        )
        scene.context(
            "IfcDuctSegment",
            "Anschluss-Luftauslass",
            [duct_solid(f, (_BRANCH_X, y0 + 0.3, z_ceiling_top + 0.02), (_BRANCH_X, y0 + 0.3, _DUCT_Z - _BRANCH_H * 0.5), 0.2, 0.2)],
        )
    scene.device("mep-cooled-beam", [box_solid(f, 0.6, 1.4, CEILING_BOTTOM - 0.12, 3.0, 2.0, z_ceiling_top + 0.02)])
    for x0, x1 in ((0.6, 2.1), (2.4, 3.6)):
        scene.device("mep-light-fixture", [box_solid(f, x0, 2.7, CEILING_BOTTOM - 0.06, x1, 2.95, z_ceiling_top + 0.02)])
    for x in (1.0, 2.3, 3.6):
        scene.device(
            "mep-fire-suppression-terminal",
            [vertical_cylinder_solid(f, x, 3.5, CEILING_BOTTOM - 0.14, 0.07, 0.22, segments=10)],
        )
    scene.device(
        "mep-alarm",
        [vertical_cylinder_solid(f, _BRANCH_X, 3.5, CEILING_BOTTOM - 0.10, 0.12, 0.16, segments=14)],
    )
    return scene.finish(params)
