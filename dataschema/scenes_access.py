"""Closures of a protected structure (Schutzbau): armoured doors, gates, hatch, lock, NEMP shield, key safe.

Every wall runs along X with its visible face at y = 0; the camera looks from +X/+Y,
so leaves, drives and housings sit on the face towards +Y.
"""

from __future__ import annotations

import math

from generators.mep_parts import box_solid, pipe_solid, vertical_cylinder_solid
from generators.wall import add_opening_in_wall

from dataschema.geometry import prism
from dataschema.scene import Scene
from dataschema.scenes_building import _floor, _wall


def _opening(s: Scene, host, name: str, origin, t: float, along: float, width: float, height: float, sill: float = 0.0) -> None:
    add_opening_in_wall(
        s.ifc_file,
        host=host,
        name=f"{name}-Oeffnung",
        body_context=s.body_context,
        along=along,
        sill=sill,
        clear_width=width,
        clear_height=height,
        wall_thickness=t,
        wall_origin=origin,
    )


def swing_leaf(f, hx: float, hy: float, length: float, angle_deg: float, thickness: float, z0: float, z1: float):
    """Door leaf hinged at ``(hx, hy)``, swung ``angle_deg`` counter-clockwise from +X."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    if angle_deg > 90.0:
        nx, ny = uy, -ux
    pts = [(hx, hy), (hx + ux * length, hy + uy * length), (hx + ux * length + nx * thickness, hy + uy * length + ny * thickness), (hx + nx * thickness, hy + ny * thickness)]
    if angle_deg > 90.0:
        pts.reverse()
    return prism(f, pts, z0, z1)


ARMOURED_AUTOMATIC = "g05-07-003-panzerturen-tore-deckel-automatisch"
ARMOURED_SWING_GATE = "g05-07-004-stahl-betonpanzerdrehflugeltore-automatisch"
ARMOURED_MANUAL = "g05-07-005-panzerturen-tore-deckel-handbetrieben"
LOCK_MANUAL = "g05-07-009-schleusen-handbetrieben"
NEMP_SHIELD = "g05-07-011-raumschirmhulle-nemp"
KEY_SAFE = "g05-07-014-tresor-fur-sz-ubergang-mit-schlusselwechsler"

_BUNKER_LENGTH = 12.0
_BUNKER_DEPTH = 6.0
_BUNKER_HEIGHT = 3.0


def _armoured_leaf(s: Scene, name: str, keys, x0: float, width: float, height: float, y_face: float = 0.0, handwheel: bool = False) -> None:
    """Closed armoured leaf standing proud of the wall face, with a frame; optional handwheel and levers."""
    f = s.ifc_file
    x1 = x0 + width
    solids = [box_solid(f, x0 - 0.02, y_face - 0.15, 0.0, x1 + 0.02, y_face + 0.08, height + 0.02)]
    if handwheel:
        xm = (x0 + x1) * 0.5
        solids += [
            pipe_solid(f, (xm, y_face + 0.08, 1.15), (xm, y_face + 0.18, 1.15), 0.03, segments=10),
            pipe_solid(f, (xm, y_face + 0.18, 1.15), (xm, y_face + 0.22, 1.15), 0.22, segments=24),
            *(box_solid(f, x1 - 0.2, y_face + 0.08, z, x1 - 0.06, y_face + 0.16, z + 0.08) for z in (0.4, 1.9)),
        ]
    s.add("IfcDoor", name, solids, keys=keys, predefined_type="DOOR")
    s.add(
        "IfcBuildingElementProxy",
        f"{name}-Zarge",
        [
            box_solid(f, x0 - 0.12, y_face, 0.0, x0 - 0.02, y_face + 0.05, height + 0.12),
            box_solid(f, x1 + 0.02, y_face, 0.0, x1 + 0.12, y_face + 0.05, height + 0.12),
            box_solid(f, x0 - 0.12, y_face, height + 0.02, x1 + 0.12, y_face + 0.05, height + 0.12),
        ],
        keys=keys,
        object_type="Panzerzarge",
    )


def protected_structure(shield: bool = False) -> Scene:
    """Protected structure room with thick walls: armoured swing gate, automatic and manual armoured doors,
    floor hatch, a manual lock chamber and a key-exchange safe at the security-zone transition.

    ``shield`` lines the room with the NEMP shielding envelope (translucent, key ``NEMP_SHIELD``).
    """
    s = Scene.new("Schutzbau")
    f = s.ifc_file
    t, length, depth, h = 0.5, _BUNKER_LENGTH, _BUNKER_DEPTH, _BUNKER_HEIGHT
    _floor(s, -t, -t, length, depth, thickness=0.5)
    origin = (-t, -t, 0.0)
    back = _wall(s, "Rueckwand", origin, length + t, h, t)
    _wall(s, "Seitenwand", (0.0, 0.0, 0.0), depth, h, t, direction=(0.0, 1.0))

    # Steel-concrete swing gate, opened by a hydraulic cylinder.
    keys = (ARMOURED_SWING_GATE, ARMOURED_AUTOMATIC)
    gx0, gw, gh = 0.8, 2.6, 2.6
    _opening(s, back, "Panzertor", origin, t, gx0 + t, gw, gh)
    angle = 70.0
    s.add("IfcDoor", "Panzerdrehfluegeltor", [swing_leaf(f, gx0, 0.0, gw, angle, 0.35, 0.0, gh)], keys=keys, predefined_type="GATE")
    s.add(
        "IfcBuildingElementProxy",
        "Torzarge",
        [box_solid(f, gx0 - 0.12, 0.0, 0.0, gx0, 0.06, gh + 0.12), box_solid(f, gx0 + gw, 0.0, 0.0, gx0 + gw + 0.12, 0.06, gh + 0.12), box_solid(f, gx0 - 0.12, 0.0, gh, gx0 + gw + 0.12, 0.06, gh + 0.12)],
        keys=keys,
        object_type="Panzerzarge",
    )
    a = math.radians(angle)
    attach = (gx0 + 1.4 * math.cos(a) + 0.35 * math.sin(a), 1.4 * math.sin(a) - 0.35 * math.cos(a) + 0.35, 2.2)
    anchor = (gx0 + gw - 0.2, 0.15, 2.2)
    mid = tuple(p + (q - p) * 0.55 for p, q in zip(anchor, attach))
    s.add("IfcActuator", "Hydraulikzylinder", [pipe_solid(f, anchor, mid, 0.07, segments=14), pipe_solid(f, mid, attach, 0.035, segments=10), box_solid(f, anchor[0] - 0.1, 0.0, 2.1, anchor[0] + 0.1, 0.12, 2.3)], keys=keys, predefined_type="HYDRAULICACTUATOR")
    s.add("IfcUnitaryControlElement", "Hydraulikaggregat", [box_solid(f, 3.65, 0.0, 0.0, 4.15, 0.45, 0.9)], keys=keys, predefined_type="CONTROLPANEL")

    # Automatic armoured door with an electro-hydraulic drive above.
    keys = (ARMOURED_AUTOMATIC,)
    _opening(s, back, "Panzertuer-automatisch", origin, t, 5.0 + t, 1.0, 2.1)
    _armoured_leaf(s, "Panzertuer-automatisch", keys, 5.0, 1.0, 2.1)
    s.add("IfcActuator", "Panzertuerantrieb", [box_solid(f, 4.85, 0.0, 2.3, 6.15, 0.22, 2.55), box_solid(f, 5.85, 0.08, 2.12, 5.95, 0.16, 2.3)], keys=keys, predefined_type="ELECTRICACTUATOR")
    s.add("IfcUnitaryControlElement", "Tuersteuerung", [box_solid(f, 6.35, 0.0, 1.0, 6.65, 0.12, 1.5)], keys=keys, predefined_type="CONTROLPANEL")

    # Manual armoured door with handwheel and a manual floor hatch.
    keys = (ARMOURED_MANUAL,)
    _opening(s, back, "Panzertuer-manuell", origin, t, 7.2 + t, 1.0, 2.1)
    _armoured_leaf(s, "Panzertuer-manuell", keys, 7.2, 1.0, 2.1, handwheel=True)
    hx, hy = 5.2, 3.8
    s.add(
        "IfcBuildingElementProxy",
        "Panzerdeckel",
        [
            box_solid(f, hx - 0.6, hy - 0.6, 0.0, hx + 0.6, hy + 0.6, 0.06),
            box_solid(f, hx - 0.5, hy - 0.5, 0.06, hx + 0.5, hy + 0.5, 0.16),
            vertical_cylinder_solid(f, hx, hy, 0.16, 0.03, 0.12, segments=10),
            vertical_cylinder_solid(f, hx, hy, 0.28, 0.2, 0.04, segments=24),
        ],
        keys=keys,
        object_type="Panzerdeckel",
    )

    # Manual lock: chamber with an armoured door in the back wall and one in the front partition,
    # overpressure valves in the partition.
    keys = (LOCK_MANUAL,)
    lx0, lx1, ly = 9.3, 11.6, 2.2
    pt = 0.3
    _opening(s, back, "Schleusentuer-aussen", origin, t, 10.0 + t, 0.9, 2.0)
    _armoured_leaf(s, "Schleusentuer-aussen", keys, 10.0, 0.9, 2.0, handwheel=True)
    s.add(
        "IfcWall",
        "Schleusenwand",
        [
            box_solid(f, lx0, 0.0, 0.0, lx0 + pt, ly + pt, h),
            box_solid(f, lx0 + pt, ly, 0.0, 10.0, ly + pt, h),
            box_solid(f, 10.9, ly, 0.0, lx1, ly + pt, h),
            box_solid(f, 10.0, ly, 2.0, 10.9, ly + pt, h),
        ],
        keys=keys,
        predefined_type="SOLIDWALL",
    )
    _armoured_leaf(s, "Schleusentuer-innen", keys, 10.0, 0.9, 2.0, y_face=ly + pt, handwheel=True)
    s.add(
        "IfcValve",
        "Ueberdruckventil",
        [pipe_solid(f, (x, ly + pt, 2.45), (x, ly + pt + 0.12, 2.45), 0.1, segments=16) for x in (9.75, 11.25)],
        keys=keys,
        predefined_type="PRESSURERELIEF",
    )
    s.add("IfcSpace", "Schleuse", [box_solid(f, lx0 + pt, 0.0, 0.0, lx1, ly, h)], dotted=True)

    # Key-exchange safe at the security-zone transition, on the side wall.
    keys = (KEY_SAFE,)
    s.add(
        "IfcBuildingElementProxy",
        "Tresor",
        [box_solid(f, 0.0, 3.4, 0.9, 0.16, 4.1, 1.55), pipe_solid(f, (0.16, 3.6, 1.22), (0.21, 3.6, 1.22), 0.06, segments=16)],
        keys=keys,
        object_type="Tresor",
    )
    s.add(
        "IfcBuildingElementProxy",
        "Schluesselwechsler",
        [box_solid(f, 0.0, 4.3, 1.0, 0.08, 4.65, 1.6), *(pipe_solid(f, (0.08, y, z), (0.12, y, z), 0.025, segments=10) for y in (4.4, 4.55) for z in (1.15, 1.3, 1.45))],
        keys=keys,
        object_type="Schluesselwechsler",
    )

    if shield:
        keys = (NEMP_SHIELD,)
        lining = 0.04
        s.add(
            "IfcCovering",
            "Raumschirmhuelle",
            [
                box_solid(f, 0.0, 0.0, 0.0, length, depth, lining),
                box_solid(f, 0.0, 0.0, lining, length, lining, h),
                box_solid(f, 0.0, lining, lining, lining, depth, h),
            ],
            keys=keys,
            predefined_type="CLADDING",
        )
        s.add("IfcBuildingElementProxy", "NEMP-Filter", [box_solid(f, 0.0, 1.0, 1.8, 0.3, 1.8, 2.6)], keys=keys, object_type="NEMP-Filter")
        s.add("IfcBuildingElementProxy", "Wabenkamin", [pipe_solid(f, (x, 0.0, 2.6), (x, 0.3, 2.6), 0.15, segments=16) for x in (4.4, 8.6)], keys=keys, object_type="Wabenkamin")
        s.volume(NEMP_SHIELD)
    return s
