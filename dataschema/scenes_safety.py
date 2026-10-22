"""Fall protection (Absturzsicherung): one scene per setting with a horizontal lifeline, a ladder
with fall-arrest rail and single anchor points; the flat roof adds a wall-mounted PSA storage cabinet.

Camera from +X/+Y: visible facades face +X and +Y.
"""

from __future__ import annotations

import math

from generators.mep_parts import box_solid, pipe_solid, vertical_cylinder_solid
from generators.parts import rect_polyline
from generators.slab import add_slab

from dataschema.geometry import profile_x
from dataschema.scene import Scene
from dataschema.scenes_building import _floor, _wall
from dataschema.scenes_rooms import corner_room, polyline_solids

PSA = "e02-06-001-personliche-schutzausrustung-gegen-absturz-psa"

# (horizontal lifeline, vertical ladder with fall-arrest rail, single anchors) per setting.
SETTINGS: dict[str, tuple[str, str, str]] = {
    "facade": (
        "e02-06-003-horizontale-absturzsicherung-aussenfassade",
        "e02-06-004-vertikale-absturzsicherung-aussenfassade",
        "e02-06-005-einzelanschlagpunkte-aussenfassade",
    ),
    "flat_roof": (
        "e02-06-006-horizontale-absturzsicherung-flachdach",
        "e02-06-007-vertikale-absturzsicherung-flachdach",
        "e02-06-008-einzelanschlagpunkte-flachdach",
    ),
    "pitched_roof": (
        "e02-06-009-horizontale-absturzsicherung-schragdach",
        "e02-06-010-vertikale-absturzsicherung-schragdach",
        "e02-06-011-einzelanschlagpunkte-schragdach",
    ),
    "interior": (
        "g05-05-002-horizontale-absturzsicherung-innenbereich",
        "g05-05-003-vertikale-absturzsicherung-innenbereich",
        "g05-05-004-einzelanschlagpunkte-innenbereich",
    ),
    "surroundings": (
        "i02-07-003-horizontale-absturzsicherung-umgebung",
        "i02-07-004-vertikale-absturzsicherung-umgebung",
        "i02-07-005-einzelanschlagpunkte-umgebung",
    ),
}

CABLE_R = 0.025


def _rect(f, p, t, n, half_t: float, half_n: float, z0: float, z1: float):
    """Box centred on plan point ``p`` with half sizes along the unit axes ``t`` and ``n``."""
    hx = abs(t[0]) * half_t + abs(n[0]) * half_n
    hy = abs(t[1]) * half_t + abs(n[1]) * half_n
    return box_solid(f, p[0] - hx, p[1] - hy, z0, p[0] + hx, p[1] + hy, z1)


def _off(p, d, k: float):
    return (p[0] + d[0] * k, p[1] + d[1] * k)


def _lifeline(s: Scene, keys, name: str, posts, height: float = 0.6) -> None:
    """Horizontal lifeline: posts ``(x, y, z_base)`` with a steel cable through their heads."""
    f = s.ifc_file
    solids = []
    for x, y, z in posts:
        solids.append(box_solid(f, x - 0.14, y - 0.14, z, x + 0.14, y + 0.14, z + 0.03))
        solids.append(vertical_cylinder_solid(f, x, y, z, 0.06, height, segments=12))
    s.add("IfcBuildingElementProxy", f"{name}-Stuetzen", solids, keys=keys, object_type="Seilstuetze", thin=True)
    cable = [(x, y, z + height - 0.05) for x, y, z in posts]
    s.add("IfcBuildingElementProxy", f"{name}-Seil", polyline_solids(f, cable, CABLE_R, segments=6), keys=keys, object_type="Sicherungsseil", thin=True)


def _wall_lifeline(s: Scene, keys, name: str, points, normal, gap: float = 0.15) -> None:
    """Facade lifeline: wall brackets at ``points`` ``(x, y, z)`` on the wall face, cable ``gap`` in front."""
    f = s.ifc_file
    t = (-normal[1], normal[0])
    brackets = []
    cable = []
    for x, y, z in points:
        brackets.append(_rect(f, _off((x, y), normal, 0.015), t, normal, 0.1, 0.015, z - 0.12, z + 0.12))
        brackets.append(_rect(f, _off((x, y), normal, gap / 2), t, normal, 0.035, gap / 2, z - 0.035, z + 0.035))
        cable.append((*_off((x, y), normal, gap), z))
    s.add("IfcBuildingElementProxy", f"{name}-Konsolen", brackets, keys=keys, object_type="Seilkonsole", thin=True)
    s.add("IfcBuildingElementProxy", f"{name}-Seil", polyline_solids(f, cable, CABLE_R, segments=6), keys=keys, object_type="Sicherungsseil", thin=True)


def _cage(f, centre, t, n, z0: float, z1: float, r: float = 0.35, spacing: float = 1.2) -> list:
    """Back-guard around the ladder at ``centre``: U-hoops from ``z0`` to ``z1`` clamped to the stiles, tied by vertical bars."""
    c = _off(centre, n, r)
    angles = [math.pi * (1 - i / 8) for i in range(9)]
    arc = [_off(_off(c, t, r * math.cos(a)), n, r * math.sin(a)) for a in angles]
    hoop = [_off(centre, t, -0.25), _off(centre, t, -r), *arc, _off(centre, t, r), _off(centre, t, 0.25)]
    count = max(1, math.ceil((z1 - z0) / spacing))
    solids = []
    for i in range(count + 1):
        z = z0 + i * (z1 - z0) / count
        solids.extend(polyline_solids(f, [(*p, z) for p in hoop], 0.02, segments=6))
    for p in arc[::2]:
        solids.append(vertical_cylinder_solid(f, p[0], p[1], z0, 0.015, z1 - z0, segments=6))
    return solids


def _ladder(
    s: Scene,
    keys,
    name: str,
    base,
    normal,
    z0: float,
    z1: float,
    extension: float = 1.0,
    gap: float = 0.2,
    cage_from: float | None = None,
) -> None:
    """Fixed ladder ``gap`` in front of the face at plan point ``base`` with a centred fall-arrest rail and runner.

    ``cage_from`` adds a back-guard starting that height above ``z0``.
    """
    f = s.ifc_file
    t = (-normal[1], normal[0])
    centre = _off(base, normal, gap)
    top = z1 + extension
    ladder = [_rect(f, _off(centre, t, side * 0.25), t, normal, 0.04, 0.04, z0, top) for side in (-1, 1)]
    z = z0 + 0.3
    while z <= z1:
        ladder.append(_rect(f, centre, t, normal, 0.25, 0.02, z, z + 0.04))
        z += 0.28
    z = z0 + 0.5
    while z < z1:
        ladder.append(_rect(f, _off(base, normal, gap / 2), t, normal, 0.3, gap / 2, z, z + 0.05))
        z += 2.0
    if cage_from is not None:
        ladder.extend(_cage(f, centre, t, normal, z0 + cage_from, top))
    s.add("IfcBuildingElementProxy", f"{name}-Steigleiter", ladder, keys=keys, object_type="Steigleiter", thin=True)
    rail = _off(centre, normal, 0.05)
    s.add("IfcBuildingElementProxy", f"{name}-Steigschutzschiene", [_rect(f, rail, t, normal, 0.04, 0.03, z0 + 0.3, top)], keys=keys, object_type="Steigschutzschiene", thin=True)
    runner = _off(centre, normal, 0.11)
    s.add("IfcBuildingElementProxy", f"{name}-Laeufer", [_rect(f, runner, t, normal, 0.07, 0.05, z0 + 1.5, z0 + 1.75)], keys=keys, object_type="Auffanglaeufer", thin=True)


def _eye(f, p, n, z: float, size: float = 0.07) -> list:
    """Square anchor eye standing out of a face along ``n``."""
    a, b = _off(p, n, 0.03), _off(p, n, 0.03 + 2 * size)
    pts = [(*a, z - size), (*b, z - size), (*b, z + size), (*a, z + size), (*a, z - size)]
    return polyline_solids(f, pts, 0.018, segments=6)


def _wall_anchors(s: Scene, keys, name: str, points, normal) -> None:
    f = s.ifc_file
    t = (-normal[1], normal[0])
    solids = []
    for x, y, z in points:
        solids.append(_rect(f, _off((x, y), normal, 0.015), t, normal, 0.09, 0.015, z - 0.09, z + 0.09))
        solids.extend(_eye(f, (x, y), normal, z))
    s.add("IfcMechanicalFastener", name, solids, keys=keys, object_type="Anschlagpunkt", thin=True)


def _post_anchors(s: Scene, keys, name: str, points, height: float = 0.45) -> None:
    f = s.ifc_file
    solids = []
    for x, y, z in points:
        solids.append(box_solid(f, x - 0.14, y - 0.14, z, x + 0.14, y + 0.14, z + 0.03))
        solids.append(vertical_cylinder_solid(f, x, y, z, 0.06, height, segments=12))
        solids.extend(_eye(f, (x - 0.1, y), (1.0, 0.0), z + height + 0.07))
    s.add("IfcMechanicalFastener", name, solids, keys=keys, object_type="Anschlagpunkt", thin=True)


def _psa_cabinet(s: Scene, p, normal, z: float, width: float = 0.7, height: float = 0.9, depth: float = 0.3) -> None:
    """Wall-mounted PSA storage cabinet on the face at plan point ``p``, bottom at ``z``, door facing ``normal``."""
    f = s.ifc_file
    t = (-normal[1], normal[0])
    hw = width / 2
    z1 = z + height
    solids = [
        _rect(f, _off(p, normal, depth / 2), t, normal, hw, depth / 2, z, z1),
        _rect(f, _off(p, normal, depth + 0.01), t, normal, hw - 0.03, 0.01, z + 0.03, z1 - 0.03),
        _rect(f, _off(_off(p, normal, depth + 0.035), t, -(hw - 0.1)), t, normal, 0.015, 0.015, z + height / 2 - 0.1, z + height / 2 + 0.1),
        _rect(f, _off(p, normal, depth + 0.025), t, normal, hw - 0.15, 0.005, z1 - 0.25, z1 - 0.1),
    ]
    s.add("IfcFurniture", "PSA-Schrank", solids, keys=(PSA,), predefined_type="USERDEFINED", object_type="PSA-Schrank", thin=True)


def _box_building(s: Scene, w: float, d: float, h: float, t: float = 0.3) -> None:
    _floor(s, -1.5, -1.5, w + 3.0, d + 4.0)
    _wall(s, "Rueckwand", (0.0, 0.0, 0.0), w, h, t)
    _wall(s, "Seitenwand", (0.0, t, 0.0), d - 2 * t, h, t, direction=(0.0, 1.0))
    _wall(s, "Fassade", (0.0, d - t, 0.0), w, h, t)
    _wall(s, "Seitenfassade", (w - t, t, 0.0), d - 2 * t, h, t, direction=(0.0, 1.0))


def _flat_roof(s: Scene, w: float, d: float, h: float) -> float:
    f = s.ifc_file
    add_slab(f, name="Dach", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, 0.0, w, d), thickness=0.3, z_bottom=h, predefined_type="ROOF")
    return h + 0.3


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def _facade(s: Scene, keys) -> None:
    f = s.ifc_file
    horizontal, vertical, single = keys
    w, d, h = 9.0, 6.0, 7.5
    _box_building(s, w, d, h)
    _flat_roof(s, w, d, h)
    bands = (1.0, 3.5, 6.0)
    s.add("IfcBuildingElementProxy", "Fensterbaender", [box_solid(f, 0.5, d, z, w - 0.5, d + 0.03, z + 1.1) for z in bands], object_type="Fensterband")
    s.add("IfcBuildingElementProxy", "Seitenfenster", [box_solid(f, w, 0.5, z, w + 0.03, 3.2, z + 1.1) for z in bands], object_type="Fensterband")

    _wall_lifeline(s, (horizontal,), "Fassadenseil", [(x, d, 7.25) for x in (0.4, 2.5, 4.5, 6.5, 8.6)], (0.0, 1.0))
    _ladder(s, (vertical,), "Fassadenleiter", (w, 4.5), (1.0, 0.0), 0.0, h + 0.3, cage_from=2.5)
    _wall_anchors(s, (single,), "Fassadenanker", [(x, d, z + 1.7) for z in bands[:2] for x in (2.0, 4.5, 7.0)], (0.0, 1.0))


def _flat(s: Scene, keys, lifeline: bool = True) -> None:
    f = s.ifc_file
    horizontal, vertical, single = keys
    w, d, h = 8.0, 6.0, 3.5
    _box_building(s, w, d, h)
    zr = _flat_roof(s, w, d, h)
    s.add("IfcBuildingElementProxy", "Dachaufbau", [box_solid(f, 0.6, 0.6, zr, 2.6, 2.6, zr + 2.2)], object_type="Dachaufbau")
    s.add("IfcUnitaryEquipment", "Monoblock", [box_solid(f, 4.8, 0.8, zr, 6.6, 2.0, zr + 1.1)], predefined_type="AIRHANDLER")

    if lifeline:
        _lifeline(s, (horizontal,), "Dachseil", [(x, 5.2, zr) for x in (0.8, 3.0, 5.2, 7.2)] + [(7.2, y, zr) for y in (3.1, 1.0)])
    _ladder(s, (vertical,), "Aufbauleiter", (2.6, 1.6), (1.0, 0.0), zr, zr + 2.2, cage_from=0.9)
    _post_anchors(s, (single,), "Dachanker", [(6.2, 3.3, zr), (4.0, 3.4, zr), (1.4, 3.8, zr)])
    _psa_cabinet(s, (1.6, 2.6), (0.0, 1.0), zr + 0.9)


def _pitched(s: Scene, keys) -> None:
    f = s.ifc_file
    horizontal, vertical, single = keys
    w, d, h, ov, thick = 9.0, 6.0, 4.0, 0.4, 0.3
    eave = h - 0.3
    ridge = eave + 2.4
    _box_building(s, w, d, h)
    roof = [(-ov, eave), (d / 2, ridge), (d + ov, eave), (d + ov, eave + thick), (d / 2, ridge + thick), (-ov, eave + thick)]
    s.add("IfcRoof", "Satteldach", [profile_x(f, roof, -ov, w + ov)], predefined_type="GABLE_ROOF")
    s.add("IfcWall", "Giebel", [profile_x(f, [(0.0, h), (d, h), (d / 2, ridge)], x0, x0 + 0.3) for x0 in (0.0, w - 0.3)], predefined_type="SOLIDWALL")
    k = (ridge - eave) / (d / 2 + ov)

    def top(y: float) -> float:
        return ridge + thick - abs(y - d / 2) * k

    s.add("IfcChimney", "Kamin", [box_solid(f, 4.2, 3.6, top(3.6) - 0.5, 4.8, 4.1, ridge + 1.0)])
    y0, y1 = 4.3, 5.2
    pane = [(y0, top(y0) - 0.02), (y1, top(y1) - 0.02), (y1, top(y1) + 0.06), (y0, top(y0) + 0.06)]
    s.add("IfcWindow", "Dachfenster", [profile_x(f, pane, x, x + 0.8) for x in (1.4, 5.4)], predefined_type="SKYLIGHT")

    _lifeline(s, (horizontal,), "Firstseil", [(x, d / 2, ridge + thick - 0.05) for x in (0.5, 2.5, 4.5, 6.5, 8.5)])

    keys_v = (vertical,)
    x = 7.5
    ya, yb = d / 2 + 0.3, d + 0.2

    def on_roof(xx: float, y: float, lift: float = 0.14) -> tuple[float, float, float]:
        return (xx, y, top(y) + lift)

    ladder = [pipe_solid(f, on_roof(x + side * 0.25, ya), on_roof(x + side * 0.25, yb), 0.035, segments=8) for side in (-1, 1)]
    y = ya + 0.2
    while y < yb:
        ladder.append(pipe_solid(f, on_roof(x - 0.25, y), on_roof(x + 0.25, y), 0.02, segments=6))
        y += 0.32
    ladder.extend(box_solid(f, x - 0.3, y - 0.04, top(y) - 0.05, x + 0.3, y + 0.04, top(y) + 0.12) for y in (ya + 0.4, (ya + yb) / 2, yb - 0.3))
    s.add("IfcBuildingElementProxy", "Dachleiter", ladder, keys=keys_v, object_type="Dachleiter", thin=True)
    s.add("IfcBuildingElementProxy", "Steigschutzschiene", [pipe_solid(f, on_roof(x, ya, 0.2), on_roof(x, yb, 0.2), 0.035, segments=8)], keys=keys_v, object_type="Steigschutzschiene", thin=True)
    s.add("IfcBuildingElementProxy", "Laeufer", [pipe_solid(f, on_roof(x, 4.6, 0.2), on_roof(x, 4.9, 0.2), 0.08, segments=10)], keys=keys_v, object_type="Auffanglaeufer", thin=True)

    _post_anchors(s, (single,), "Dachanker", [(x0, y0, top(y0) - 0.05) for x0, y0 in ((1.0, 3.9), (3.2, 5.2), (5.8, 3.8))], height=0.4)


def _interior(s: Scene, keys) -> None:
    f = s.ifc_file
    horizontal, vertical, single = keys
    zp = 3.0
    s.add("IfcSlab", "Buehne", [box_solid(f, 0.0, 0.0, zp - 0.2, 6.5, 3.5, zp)], predefined_type="FLOOR")
    s.add("IfcColumn", "Buehnenstuetzen", [box_solid(f, x - 0.1, 3.25, 0.0, x + 0.1, 3.45, zp - 0.2) for x in (2.5, 6.35)], predefined_type="COLUMN")
    s.add("IfcBuildingElementProxy", "Lagergut", [box_solid(f, 0.3, 0.3, zp, 1.4, 1.4, zp + 0.9), box_solid(f, 1.6, 0.3, zp, 2.7, 1.4, zp + 0.9)], object_type="Palette")
    s.add("IfcBuildingElementProxy", "Maschine", [box_solid(f, 7.5, 0.5, 0.0, 9.5, 2.3, 2.5)], object_type="Maschine")

    _lifeline(s, (horizontal,), "Buehnenseil", [(x, 3.15, zp) for x in (0.4, 2.0, 3.6, 5.2)], height=1.1)
    _ladder(s, (vertical,), "Buehnenleiter", (5.95, 3.5), (0.0, 1.0), 0.0, zp, cage_from=2.2)
    _wall_anchors(s, (single,), "Wandanker", [(x, 0.0, 4.0) for x in (7.8, 8.5, 9.2)], (0.0, 1.0))


def _surroundings(s: Scene, keys) -> None:
    f = s.ifc_file
    horizontal, vertical, single = keys
    zt = 3.0
    add_slab(f, name="Terrain", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, 0.0, 14.0, 11.0), thickness=0.4, z_bottom=-0.4, predefined_type="BASESLAB")
    s.add("IfcBuildingElementProxy", "Gelaende-oben", [box_solid(f, 0.0, 0.0, 0.0, 14.0, 4.0, zt)], object_type="Gelaende")
    s.add("IfcWall", "Stuetzmauer", [box_solid(f, 0.0, 4.0, 0.0, 14.0, 4.3, zt + 0.15)], predefined_type="SOLIDWALL")

    _lifeline(s, (horizontal,), "Mauerseil", [(x, 3.5, zt) for x in (0.6, 4.9, 9.1, 13.4)], height=1.1)
    _ladder(s, (vertical,), "Mauerleiter", (7.0, 4.3), (0.0, 1.0), 0.0, zt + 0.15, cage_from=2.2)

    sx, sy = 4.0, 8.0
    s.add("IfcDistributionChamberElement", "Schacht", [vertical_cylinder_solid(f, sx, sy, -0.05, 0.75, 0.15, segments=24)], predefined_type="MANHOLE")
    s.add("IfcBuildingElementProxy", "Schachtdeckel", [box_solid(f, sx + 0.8, sy - 0.4, 0.0, sx + 1.6, sy + 0.4, 0.06)], object_type="Schachtdeckel")
    _post_anchors(s, (single,), "Bodenanker", [(sx - 1.1, sy - 0.6, 0.0), (sx - 1.1, sy + 0.6, 0.0), (sx, sy + 1.2, 0.0)], height=0.6)


_BUILDERS = {
    "facade": _facade,
    "flat_roof": _flat,
    "pitched_roof": _pitched,
    "interior": _interior,
    "surroundings": _surroundings,
}


def fall_protection(setting: str, lifeline: bool = True) -> Scene:
    """Fall protection in ``setting`` (facade, flat_roof, pitched_roof, interior, surroundings).

    ``lifeline=False`` drops the horizontal lifeline (flat roof only).
    """
    if setting not in SETTINGS:
        raise ValueError(f"unknown fall-protection setting {setting!r}")
    if setting == "interior":
        s = corner_room("Absturzsicherung-Innen", width=10.0, depth=7.0, height=5.5)
    else:
        s = Scene.new(f"Absturzsicherung-{setting}", storey_name="Terrain" if setting == "surroundings" else "EG")
    if setting == "flat_roof":
        _flat(s, SETTINGS[setting], lifeline=lifeline)
    else:
        _BUILDERS[setting](s, SETTINGS[setting])
    return s
