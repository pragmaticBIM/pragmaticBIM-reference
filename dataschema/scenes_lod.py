"""Detail-level vignettes (hoch / mitte / tief) for arma-master-bestandsaufnahme.

One builder per element family; the three levels share context and framing so
they compare 1:1, only the accented element follows the Modellierungshinweis
of its level. Levels whose element is not modelled show it as a translucent
ghost volume. Openings are boolean differences so cut faces stay seamless.
"""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.mep_parts import box_solid, duct_solid, pipe_solid, vertical_cylinder_solid
from generators.parts import create_oriented_extruded_solid

from dataschema.geometry import frustum, prism, profile_x, profile_y
from dataschema.render import Card
from dataschema.scene import Scene

HOCH, MITTE, TIEF = "hoch", "mitte", "tief"
LEVELS = (HOCH, MITTE, TIEF)


def _cut(f: ifcopenshell.file, solid: ifcopenshell.entity_instance, *cutters: ifcopenshell.entity_instance) -> ifcopenshell.entity_instance:
    for cutter in cutters:
        solid = f.create_entity("IfcBooleanResult", Operator="DIFFERENCE", FirstOperand=solid, SecondOperand=cutter)
    return solid


def _add(s: Scene, ifc_class: str, name: str, solids: Sequence[ifcopenshell.entity_instance], **kwargs) -> ifcopenshell.entity_instance:
    product = s.add(ifc_class, name, solids, **kwargs)
    if any(solid.is_a("IfcBooleanResult") for solid in solids):
        product.Representation.Representations[0].RepresentationType = "CSG"
    return product


def _ring(f: ifcopenshell.file, x0: float, z0: float, x1: float, z1: float, width: float, y0: float, y1: float) -> ifcopenshell.entity_instance:
    """Rectangular frame in the XZ plane, ``width`` wide, from ``y0`` to ``y1`` deep."""
    return _cut(f, box_solid(f, x0, y0, z0, x1, y1, z1), box_solid(f, x0 + width, y0 - 0.1, z0 + width, x1 - width, y1 + 0.1, z1 - width))


def _frame(f: ifcopenshell.file, x0: float, x1: float, top: float, width: float, y0: float, y1: float) -> ifcopenshell.entity_instance:
    """Door frame (two jambs and a head) standing on the floor."""
    return _cut(f, box_solid(f, x0, y0, 0.0, x1, y1, top), box_solid(f, x0 + width, y0 - 0.1, -0.1, x1 - width, y1 + 0.1, top - width))


def _floor(s: Scene, x0: float, y0: float, x1: float, y1: float, z: float = 0.0, *, dotted: bool = False, name: str = "Boden") -> None:
    s.add("IfcSlab", name, [box_solid(s.ifc_file, x0, y0, z - 0.25, x1, y1, z)], predefined_type="FLOOR", dotted=dotted)


def _back_walls(s: Scene, x1: float, y1: float, height: float, t: float = 0.2) -> None:
    """Walls along the far edges (y = 0 and x = 0) of a room from the origin to ``(x1, y1)``."""
    f = s.ifc_file
    s.add("IfcWall", "Rueckwand", [box_solid(f, -t, -t, 0.0, x1, 0.0, height)], predefined_type="SOLIDWALL")
    s.add("IfcWall", "Seitenwand", [box_solid(f, -t, 0.0, 0.0, 0.0, y1, height)], predefined_type="SOLIDWALL")


def _i_section(c: float, z0: float, width: float, height: float, web: float, flange: float) -> list[tuple[float, float]]:
    """I-section centred on ``c`` (horizontal) from ``z0`` to ``z0 + height``."""
    a, b, w = c - width / 2, c + width / 2, web / 2
    z1 = z0 + height
    return [
        (a, z0), (b, z0), (b, z0 + flange), (c + w, z0 + flange), (c + w, z1 - flange), (b, z1 - flange),
        (b, z1), (a, z1), (a, z1 - flange), (c - w, z1 - flange), (c - w, z0 + flange), (a, z0 + flange),
    ]


# ---------------------------------------------------------------------------
# Building envelope
# ---------------------------------------------------------------------------

WALL = "wand"


def walls(level: str) -> Scene:
    """hoch: profiled sweeps and V joint; mitte: rectangular sweeps and joint; tief: flat slab without openings."""
    s = Scene.new("Waende")
    f = s.ifc_file
    length, t, h = 5.0, 0.25, 2.8
    d0, d1, dh = 3.3, 4.3, 2.1
    _floor(s, -0.6, -0.6, length + 0.6, 2.0)
    if level == TIEF:
        s.add("IfcWall", "Wand", [box_solid(f, 0.0, 0.0, 0.0, length, t, h)], keys=(WALL,), predefined_type="SOLIDWALL")
        return s
    joint = 1.7
    if level == HOCH:
        groove = [(joint - 0.045, t + 0.01), (joint, t - 0.04), (joint + 0.045, t + 0.01)]
        skirting = [(t, 0.0), (t + 0.03, 0.0), (t + 0.03, 0.08), (t + 0.012, 0.13), (t, 0.13)]
        cornice = [(t, h - 0.2), (t + 0.02, h - 0.17), (t + 0.04, h - 0.1), (t + 0.07, h - 0.06), (t + 0.07, h), (t, h)]
    else:
        groove = [(joint - 0.035, t - 0.03), (joint + 0.035, t - 0.03), (joint + 0.035, t + 0.01), (joint - 0.035, t + 0.01)]
        skirting = [(t, 0.0), (t + 0.03, 0.0), (t + 0.03, 0.12), (t, 0.12)]
        cornice = [(t, h - 0.14), (t + 0.06, h - 0.14), (t + 0.06, h), (t, h)]
    body = _cut(f, box_solid(f, 0.0, 0.0, 0.0, length, t, h), box_solid(f, d0, -0.1, -0.1, d1, t + 0.1, dh), prism(f, groove, -0.1, h + 0.1))
    sweeps = [profile_x(f, skirting, 0.0, d0), profile_x(f, skirting, d1, length), profile_x(f, cornice, 0.0, length)]
    _add(s, "IfcWall", "Wand", [body, *sweeps], keys=(WALL,), predefined_type="SOLIDWALL")
    s.add("IfcDoor", "Tuer", [box_solid(f, d0 + 0.03, t / 2 - 0.02, 0.0, d1 - 0.03, t / 2 + 0.02, dh - 0.03)], predefined_type="DOOR")
    return s


WINDOW = "fenster"


def windows(level: str) -> Scene:
    """hoch: sashes with glazing bars, shaped sills; mitte: plain sashes, box sill; tief: one pane in a prismatic lining."""
    s = Scene.new("Fenster")
    f = s.ifc_file
    length, t, h = 3.0, 0.3, 2.8
    x0, x1, z0, z1 = 0.9, 2.1, 0.9, 2.3
    _floor(s, -0.5, -0.8, length + 0.5, 1.2)
    wall = _cut(f, box_solid(f, 0.0, 0.0, 0.0, length, t, h), box_solid(f, x0, -0.1, z0, x1, t + 0.1, z1))
    _add(s, "IfcWall", "Aussenwand", [wall], predefined_type="SOLIDWALL")
    window: list[ifcopenshell.entity_instance] = []
    panes: list[ifcopenshell.entity_instance] = []
    if level == TIEF:
        lining = 0.04
        window.append(_ring(f, x0, z0, x1, z1, lining, 0.0, t))
        panes.append(box_solid(f, x0 + lining, 0.14, z0 + lining, x1 - lining, 0.16, z1 - lining))
    else:
        fy0, fy1, fw, sw = 0.1, 0.18, 0.06, 0.055
        xm = (x0 + x1) / 2
        window += [_ring(f, x0, z0, x1, z1, fw, fy0, fy1), box_solid(f, xm - 0.03, fy0, z0, xm + 0.03, fy1, z1)]
        for a, b in ((x0 + fw, xm - 0.03), (xm + 0.03, x1 - fw)):
            window.append(_ring(f, a, z0 + fw, b, z1 - fw, sw, fy0 + 0.02, fy1 + 0.02))
            ga, gb, gz0, gz1 = a + sw, b - sw, z0 + fw + sw, z1 - fw - sw
            panes.append(box_solid(f, ga, 0.145, gz0, gb, 0.155, gz1))
            if level == HOCH:
                bar, gm = 0.025, (ga + gb) / 2
                window.append(box_solid(f, gm - bar / 2, 0.13, gz0, gm + bar / 2, 0.17, gz1))
                for k in (1, 2):
                    z = gz0 + (gz1 - gz0) * k / 3
                    window.append(box_solid(f, ga, 0.13, z - bar / 2, gb, 0.17, z + bar / 2))
        if level == HOCH:
            sill = [(fy1, z0 - 0.01), (t + 0.04, z0 - 0.02), (t + 0.04, z0 - 0.04), (t + 0.065, z0 - 0.04), (t + 0.065, z0), (fy1, z0 + 0.03)]
            window += [profile_x(f, sill, x0 - 0.04, x1 + 0.04), box_solid(f, x0 - 0.05, -0.05, z0, x1 + 0.05, fy0, z0 + 0.025)]
        else:
            window.append(box_solid(f, x0 - 0.03, fy1, z0 - 0.04, x1 + 0.03, t + 0.05, z0 + 0.02))
    _add(s, "IfcWindow", "Fenster", window, keys=(WINDOW,), predefined_type="WINDOW")
    for i, pane in enumerate(panes):
        s.add("IfcPlate", f"Glas-{i + 1}", [pane], predefined_type="CURTAIN_PANEL")
    return s


DOOR = "tuer"


def doors(level: str) -> Scene:
    """hoch: lining, architraves, panelled leaf, handle, threshold; mitte: frame and flat leaf; tief: one block."""
    s = Scene.new("Tueren")
    f = s.ifc_file
    length, t, h = 3.5, 0.15, 2.8
    x0, x1, dh = 1.2, 2.2, 2.1
    _floor(s, -0.5, -0.8, length + 0.5, 1.4)
    _add(s, "IfcWall", "Innenwand", [_cut(f, box_solid(f, 0.0, 0.0, 0.0, length, t, h), box_solid(f, x0, -0.1, -0.1, x1, t + 0.1, dh))], predefined_type="PARTITIONING")
    if level == TIEF:
        door = [box_solid(f, x0, 0.0, 0.0, x1, t, dh)]
    elif level == MITTE:
        fw = 0.05
        door = [_frame(f, x0, x1, dh, fw, -0.01, t + 0.01), box_solid(f, x0 + fw, t - 0.05, 0.005, x1 - fw, t - 0.01, dh - fw)]
    else:
        fw, aw = 0.04, 0.07
        lx0, lx1, lz1, ly0, ly1, stile = x0 + fw, x1 - fw, dh - fw, t - 0.055, t - 0.01, 0.12
        fields = [box_solid(f, lx0 + stile, ly1 - 0.012, z_lo, lx1 - stile, ly1 + 0.1, z_hi) for z_lo, z_hi in ((0.18, 0.95), (1.12, lz1 - stile))]
        door = [
            _frame(f, x0, x1, dh, fw, 0.0, t),
            _frame(f, x0 - aw + fw, x1 + aw - fw, dh + aw - fw, aw, t, t + 0.015),
            _frame(f, x0 - aw + fw, x1 + aw - fw, dh + aw - fw, aw, -0.015, 0.0),
            _cut(f, box_solid(f, lx0, ly0, 0.015, lx1, ly1, lz1), *fields),
            box_solid(f, lx1 - 0.11, ly1, 0.97, lx1 - 0.05, ly1 + 0.012, 1.13),
            box_solid(f, lx1 - 0.09, ly1, 1.03, lx1 - 0.07, ly1 + 0.07, 1.05),
            box_solid(f, lx1 - 0.24, ly1 + 0.05, 1.03, lx1 - 0.07, ly1 + 0.07, 1.05),
            box_solid(f, x0, 0.0, 0.0, x1, t, 0.012),
        ]
    _add(s, "IfcDoor", "Tuer", door, keys=(DOOR,), predefined_type="DOOR")
    return s


FACADE = "fassade"
_BAYS = (0.0, 1.5, 3.0, 4.5, 6.0)
_ROWS = (0.0, 0.9, 2.7, 3.4)
_DOOR_BAY = 2


def facade(level: str) -> Scene:
    """hoch: profiled mullions with cover caps; mitte: rectangular grid; tief: opaque and transparent fields only."""
    s = Scene.new("Fassade")
    f = s.ifc_file
    top = _ROWS[-1]
    _floor(s, -0.4, -3.0, _BAYS[-1] + 0.4, 0.0)
    _floor(s, -0.4, -3.0, _BAYS[-1] + 0.4, 0.0, top + 0.25, dotted=True, name="Decke")
    cells = []
    for i in range(len(_BAYS) - 1):
        for j in range(len(_ROWS) - 1):
            if i == _DOOR_BAY and j == 0:
                cells.append((_BAYS[i], _ROWS[0], _BAYS[i + 1], _ROWS[2], "door"))
            elif not (i == _DOOR_BAY and j == 1):
                cells.append((_BAYS[i], _ROWS[j], _BAYS[i + 1], _ROWS[j + 1], "glass" if j == 1 else "opaque"))
    wall: list[ifcopenshell.entity_instance] = []
    glass: list[ifcopenshell.entity_instance] = []
    door: list[ifcopenshell.entity_instance] = []
    if level == TIEF:
        for x0, z0, x1, z1, kind in cells:
            if kind == "opaque":
                wall.append(box_solid(f, x0, 0.04, z0, x1, 0.12, z1))
            else:
                glass.append(box_solid(f, x0, 0.07, z0, x1, 0.09, z1))
    else:
        m = 0.06 if level == HOCH else 0.05
        for x in _BAYS:
            wall.append(box_solid(f, x - m / 2, 0.02, -m / 2, x + m / 2, 0.14, top + m / 2))
            if level == HOCH:
                wall.append(box_solid(f, x - 0.025, 0.14, -m / 2, x + 0.025, 0.18, top + m / 2))
        for i in range(len(_BAYS) - 1):
            for z in _ROWS:
                if i == _DOOR_BAY and z == _ROWS[1]:
                    continue
                xa, xb = _BAYS[i] + m / 2, _BAYS[i + 1] - m / 2
                wall.append(box_solid(f, xa, 0.02, z - m / 2, xb, 0.14, z + m / 2))
                if level == HOCH:
                    wall.append(box_solid(f, xa, 0.14, z - 0.025, xb, 0.18, z + 0.025))
        for x0, z0, x1, z1, kind in cells:
            xa, za, xb, zb = x0 + m / 2, z0 + m / 2, x1 - m / 2, z1 - m / 2
            if kind == "opaque":
                wall.append(box_solid(f, xa, 0.06, za, xb, 0.1, zb))
            elif kind == "glass":
                glass.append(box_solid(f, xa, 0.075, za, xb, 0.085, zb))
            else:
                xm = (xa + xb) / 2
                door += [_frame(f, xa, xb, zb, 0.08, 0.04, 0.12), box_solid(f, xm - 0.03, 0.04, 0.0, xm + 0.03, 0.12, zb)]
                glass += [box_solid(f, a, 0.075, 0.08, b, 0.085, zb - 0.08) for a, b in ((xa + 0.08, xm - 0.03), (xm + 0.03, xb - 0.08))]
    _add(s, "IfcCurtainWall", "Fassade", wall, keys=(FACADE,))
    if door:
        _add(s, "IfcDoor", "Eingang", door, predefined_type="DOOR")
    for i, pane in enumerate(glass):
        s.add("IfcPlate", f"Glas-{i + 1}", [pane], predefined_type="CURTAIN_PANEL")
    return s


ROOF = "dach"
_EAVE, _RIDGE, _YM, _DEPTH, _WIDTH = 2.6, 4.4, 2.5, 5.0, 6.0
_PITCH = (_RIDGE - _EAVE) / _YM


def _roof_z(y: float) -> float:
    return _RIDGE - _PITCH * abs(y - _YM)


def _gable(y_lo: float, y_hi: float, o0: float, o1: float) -> list[tuple[float, float]]:
    """Gable roof section (y, z) between vertical offsets ``o0`` and ``o1`` above the roof plane."""
    return [
        (y_lo, _roof_z(y_lo) + o0), (_YM, _RIDGE + o0), (y_hi, _roof_z(y_hi) + o0),
        (y_hi, _roof_z(y_hi) + o1), (_YM, _RIDGE + o1), (y_lo, _roof_z(y_lo) + o1),
    ]


def _slope_band(y0: float, y1: float, o0: float, o1: float) -> list[tuple[float, float]]:
    """Section (y, z) of a strip on the front slope between ``y0`` and ``y1``."""
    return [(y0, _roof_z(y0) + o0), (y1, _roof_z(y1) + o0), (y1, _roof_z(y1) + o1), (y0, _roof_z(y0) + o1)]


def _i_rafter(f: ifcopenshell.file, x: float, y0: float, y1: float, height: float = 0.32) -> ifcopenshell.entity_instance:
    """I-profile rafter hanging under the roof plane from ``y0`` to ``y1`` (one slope), round openings in the web."""
    run = y1 - y0
    slope = -_PITCH if y0 >= _YM else _PITCH
    norm = (1.0 + _PITCH**2) ** 0.5
    axis = (0.0, 1.0 / norm, slope / norm)
    normal = (0.0, -axis[2], axis[1])  # profile Y, perpendicular to the slope and pointing up
    origin = (x, y0, _roof_z(y0))
    length = run * norm
    section = [(-u, n) for u, n in _i_section(0.0, -height, 0.1, height, 0.012, 0.025)]
    rafter = create_oriented_extruded_solid(f, section, length, origin=origin, axis=axis, ref_direction=(-1.0, 0.0, 0.0))
    holes = []
    for i in range(int((length - 0.7) / 0.45)):
        s = 0.45 + 0.45 * i
        cy, cz = (origin[k] + axis[k] * s - normal[k] * height / 2 for k in (1, 2))
        # 32 facets stay below the 15° crease angle, so the openings read round.
        holes.append(pipe_solid(f, (x - 0.05, cy, cz), (x + 0.05, cy, cz), 0.1, segments=32))
    return _cut(f, rafter, *holes)


def roofs(level: str) -> Scene:
    """The front slope is cut away at the near gable to show the build-up.

    hoch: three layers stepped back at the cut, I-profile rafters with web openings, eave and barge boards, ridge cap,
    roof window and detailed chimney; mitte: one layer on regular rafters, openings for roof window and chimney;
    tief: one solid layer only.
    """
    s = Scene.new("Dach")
    f = s.ifc_file
    w, d, t, ov = _WIDTH, _DEPTH, 0.25, 0.4
    _floor(s, -0.8, -0.8, w + 0.8, d + 0.8)
    _add(s, "IfcWall", "Aussenwaende", [_cut(f, box_solid(f, 0.0, 0.0, 0.0, w, d, _EAVE), box_solid(f, 0.25, 0.25, -0.1, w - 0.25, d - 0.25, _EAVE + 0.1))], predefined_type="SOLIDWALL")
    s.add("IfcWall", "Giebel", [profile_x(f, [(0.0, _EAVE), (d, _EAVE), (_YM, _RIDGE)], x, x + 0.25) for x in (0.0, w - 0.25)], predefined_type="SOLIDWALL")
    win = (1.95, 2.85, 3.3, 4.2)
    chimney = (1.2, 1.8, 3.0, 3.5)
    cut_x = 3.3

    def opening(x0: float) -> ifcopenshell.entity_instance:
        return box_solid(f, x0, _YM, 0.0, w + ov + 1.0, d + ov + 1.0, 10.0)

    holes = [box_solid(f, xa, ya, 0.0, xb, yb, 10.0) for xa, xb, ya, yb in (win, chimney)] if level != TIEF else []
    if level == HOCH:
        layers = [(0.0, 0.16, ov, cut_x), (0.16, 0.21, ov, cut_x - 0.15), (0.21, t, ov + 0.05, cut_x - 0.3)]
    else:
        layers = [(0.0, t, ov, cut_x)]
    roof = [_cut(f, profile_x(f, _gable(-o, d + o, o0, o1), -o, w + o), *holes, opening(x0)) for o0, o1, o, x0 in layers]
    if level == HOCH:
        eave = d + ov
        cap_z = _RIDGE + t - _PITCH * 0.12
        roof += [
            _cut(f, box_solid(f, -ov, eave, _roof_z(eave) - 0.12, w + ov, eave + 0.03, _roof_z(eave) + 0.21), opening(cut_x - 0.3)),
            _cut(f, profile_x(f, _gable(-ov, d + ov, -0.12, 0.21), w + ov, w + ov + 0.03), opening(cut_x - 0.3)),
            _cut(f, profile_x(f, [(_YM - 0.12, cap_z), (_YM + 0.12, cap_z), (_YM, _RIDGE + t + 0.08)], -ov - 0.05, w + ov + 0.05), opening(cut_x - 0.3)),
        ]
    _add(s, "IfcRoof", "Dach", roof, keys=(ROOF,), predefined_type="GABLE_ROOF")
    if level != TIEF:
        xs = [0.5 + 0.6 * i for i in range(9)]
        if level == MITTE:
            rafters = [_cut(f, profile_x(f, _gable(-ov + 0.02, d + ov - 0.02, -0.2, 0.0), x - 0.06, x + 0.06), *holes) for x in xs]
        else:
            rafters = [
                _i_rafter(f, x, y0, y1)
                for x in xs
                if not any(xa - 0.1 < x < xb + 0.1 for xa, xb, _, _ in (win, chimney))
                for y0, y1 in ((-ov + 0.02, _YM), (_YM, d + ov - 0.02))
            ]
        _add(s, "IfcMember", "Sparren", rafters, keys=(ROOF,), predefined_type="RAFTER")
    if level == TIEF:
        return s
    xa, xb, ya, yb = win
    frame = [profile_x(f, _slope_band(ya, yb, 0.0, t + 0.06), xa, xb)]
    if level == HOCH:
        frame.append(profile_x(f, _slope_band(ya - 0.08, yb + 0.08, t - 0.02, t + 0.01), xa - 0.08, xb + 0.08))
    s.add("IfcWindow", "Dachfenster", frame, predefined_type="SKYLIGHT")
    s.add("IfcPlate", "Dachfenster-Glas", [profile_x(f, _slope_band(ya + 0.06, yb - 0.06, t + 0.06, t + 0.07), xa + 0.06, xb - 0.06)], predefined_type="CURTAIN_PANEL")
    ca, cb, cy0, cy1 = chimney
    stack = [box_solid(f, ca, cy0, _EAVE, cb, cy1, 5.0)]
    if level == HOCH:
        stack += [box_solid(f, ca - 0.08, cy0 - 0.08, 5.0, cb + 0.08, cy1 + 0.08, 5.07)]
        stack += [vertical_cylinder_solid(f, x, (cy0 + cy1) / 2, 5.07, 0.07, 0.25) for x in (ca + 0.15, cb - 0.15)]
    s.add("IfcChimney", "Kamin", stack)
    return s


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

SLAB = "decke"


def slabs(level: str) -> Scene:
    """hoch: concrete plus floor finish with a shaft opening; mitte: one layer with the opening; tief: flat plate."""
    s = Scene.new("Decken")
    f = s.ifc_file
    w, d = 5.0, 4.0
    s.add("IfcWall", "Wand-Front", [box_solid(f, 0.0, d - 0.25, -1.6, w, d, -0.25)], predefined_type="SOLIDWALL")
    s.add("IfcWall", "Wand-Seite", [box_solid(f, w - 0.25, 0.0, -1.6, w, d - 0.25, -0.25)], predefined_type="SOLIDWALL")
    shaft = box_solid(f, 3.0, 0.7, -1.0, 3.8, 1.5, 1.0)
    if level == HOCH:
        slab = [_cut(f, box_solid(f, 0.0, 0.0, -0.25, w, d, 0.0), shaft), _cut(f, box_solid(f, 0.0, 0.0, 0.0, w, d, 0.08), shaft)]
    elif level == MITTE:
        slab = [_cut(f, box_solid(f, 0.0, 0.0, -0.25, w, d, 0.08), shaft)]
    else:
        slab = [box_solid(f, 0.0, 0.0, -0.25, w, d, 0.08)]
    _add(s, "IfcSlab", "Decke", slab, keys=(SLAB,), predefined_type="FLOOR")
    return s


COLUMN = "stuetze"


def columns(level: str) -> Scene:
    """Steel and concrete column. hoch: HEB with plates, chamfered concrete with plinth and capital;
    mitte: plain I-profile and square column; tief: rectangular boxes."""
    s = Scene.new("Stuetzen")
    f = s.ifc_file
    h = 3.0
    _floor(s, -0.6, -0.6, 3.4, 1.6)
    _floor(s, -0.6, -0.6, 3.4, 1.6, h + 0.25, dotted=True, name="Decke")
    sx, sy, cx, cy = 0.7, 0.5, 2.2, 0.5
    b, c = 0.24, 0.35
    i_plan = _i_section(sx, sy - b / 2, b, b, 0.012, 0.02)
    if level == TIEF:
        steel = [box_solid(f, sx - b / 2, sy - b / 2, 0.0, sx + b / 2, sy + b / 2, h)]
        concrete = [box_solid(f, cx - c / 2, cy - c / 2, 0.0, cx + c / 2, cy + c / 2, h)]
    elif level == MITTE:
        steel = [prism(f, i_plan, 0.0, h)]
        concrete = [box_solid(f, cx - c / 2, cy - c / 2, 0.0, cx + c / 2, cy + c / 2, h)]
    else:
        steel = [
            box_solid(f, sx - 0.2, sy - 0.2, 0.0, sx + 0.2, sy + 0.2, 0.03),
            prism(f, i_plan, 0.03, h - 0.02),
            box_solid(f, sx - 0.15, sy - 0.15, h - 0.02, sx + 0.15, sy + 0.15, h),
            *(vertical_cylinder_solid(f, sx + dx, sy + dy, 0.03, 0.015, 0.04, segments=8) for dx in (-0.16, 0.16) for dy in (-0.16, 0.16)),
        ]
        e, k = c / 2, 0.03
        octagon = [(cx - e + k, cy - e), (cx + e - k, cy - e), (cx + e, cy - e + k), (cx + e, cy + e - k), (cx + e - k, cy + e), (cx - e + k, cy + e), (cx - e, cy + e - k), (cx - e, cy - e + k)]
        concrete = [
            box_solid(f, cx - 0.23, cy - 0.23, 0.0, cx + 0.23, cy + 0.23, 0.15),
            prism(f, octagon, 0.15, h - 0.25),
            frustum(f, cx, cy, h, h - 0.25, (0.26, 0.26), (e, e)),
        ]
    s.add("IfcColumn", "Stahlstuetze", steel, keys=(COLUMN,), predefined_type="COLUMN")
    s.add("IfcColumn", "Betonstuetze", concrete, keys=(COLUMN,), predefined_type="COLUMN")
    return s


BEAM = "traeger"


def beams(level: str) -> Scene:
    """hoch: I-beams with round pipe openings in the web; mitte: plain I-beams; tief: rectangles. Slab dotted."""
    s = Scene.new("Unterzuege")
    f = s.ifc_file
    w, d, h, bh = 6.0, 4.0, 3.3, 0.3
    _floor(s, -0.6, -0.6, w + 0.6, d + 0.6)
    _floor(s, -0.3, -0.3, w + 0.3, d + 0.3, h + 0.25, dotted=True, name="Decke")
    for x in (0.0, w):
        for y in (0.0, d):
            s.add("IfcColumn", f"Stuetze-{x}-{y}", [box_solid(f, x - 0.15, y - 0.15, 0.0, x + 0.15, y + 0.15, h - bh)], predefined_type="COLUMN")
    beam = []
    for y in (0.0, d):
        if level == TIEF:
            beam.append(box_solid(f, -0.15, y - 0.09, h - bh, w + 0.15, y + 0.09, h))
            continue
        profile = profile_x(f, _i_section(y, h - bh, 0.18, bh, 0.012, 0.02), -0.15, w + 0.15)
        if level == HOCH:
            # 32 facets stay below the 15° crease angle, so the openings read round.
            holes = [pipe_solid(f, (x, y - 0.05, h - bh / 2), (x, y + 0.05, h - bh / 2), 0.09, segments=32) for x in (1.2, 2.4, 3.6, 4.8)]
            profile = _cut(f, profile, *holes)
        beam.append(profile)
    _add(s, "IfcBeam", "Unterzuege", beam, keys=(BEAM,), predefined_type="BEAM")
    return s


STAIR = "treppe"


def stairs(level: str) -> Scene:
    """Concrete flight with a sloped soffit on every level.

    tief: flight only, standing on the floor; mitte: flight on elastomer bearings set into pockets of the floor
    and the landing, the top step extended into the landing; hoch: as mitte, plus tread and riser covering with
    nosing and a joint to the stairwell wall.
    """
    s = Scene.new("Treppe")
    f = s.ifc_file
    n, rise, go, width, landing_t = 12, 0.175, 0.28, 1.2, 0.3
    run, top = (n - 1) * go, n * rise
    waist = landing_t * go / (go**2 + rise**2) ** 0.5  # soffit meets the landing underside flush
    pad = 0.03
    gap = 0.02 if level == HOCH else 0.0
    tongue, tongue_t, foot_len, joint = 0.25, 0.2, 0.3, 0.02  # tongue_t > rise, or the tongue detaches from the flight
    if level == TIEF:
        _floor(s, -1.4, -0.6, run + 1.0, width + 0.8)
    else:
        floor = box_solid(f, -1.4, -0.6, -0.25, run + 1.0, width + 0.8, 0.0)
        pocket = box_solid(f, run - foot_len - joint, gap - joint, -pad, run + joint, width + joint, 0.01)
        _add(s, "IfcSlab", "Boden", [_cut(f, floor, pocket)], predefined_type="FLOOR")
    s.add("IfcWall", "Treppenhauswand", [box_solid(f, -1.4, -0.2, 0.0, run + 1.0, 0.0, top + 0.9)], predefined_type="SOLIDWALL")
    treads = [(run - (i + 1) * go, run - i * go, (i + 1) * rise) for i in range(n - 1)]
    drop = waist * (go**2 + rise**2) ** 0.5 / go

    def soffit(x: float) -> float:
        """Underside parallel to the nosing line ``z = (run - x) * rise / go + rise``, one waist lower."""
        return (run - x) * rise / go + rise - drop

    steps = [(run, 0.0)]
    for xa, xb, z in treads:
        steps += [(xb, z), (xa, z)]
    landing = box_solid(f, -1.4, -0.2, top - landing_t, 0.0, width, top)
    if level == TIEF:
        s.add("IfcSlab", "Podest", [landing], predefined_type="LANDING")
        flight = [*steps, (0.0, soffit(0.0)), (run - (drop - rise) * go / rise, 0.0)]
    else:
        # The top step runs on into a landing pocket; both bearings lie flush inside the slabs.
        seat = top - tongue_t
        pocket = box_solid(f, -tongue - joint, gap - joint, seat - pad, 0.01, width + joint, top + 0.01)
        _add(s, "IfcSlab", "Podest", [_cut(f, landing, pocket)], predefined_type="LANDING")
        flight = [
            *steps,
            (0.0, top),
            (-tongue, top),
            (-tongue, seat),
            (joint, seat),
            (joint, soffit(joint)),
            (run - foot_len, soffit(run - foot_len)),
            (run - foot_len, 0.0),
        ]
        s.add(
            "IfcDiscreteAccessory",
            "Auflager",
            [box_solid(f, run - foot_len, gap, -pad, run, width, 0.0), box_solid(f, -tongue, gap, seat - pad, 0.0, width, seat)],
            object_type="Elastomerlager",
        )
    parts = [profile_y(f, flight, gap, width)]
    if level == HOCH:
        cover = 0.03
        for i, (xa, xb, z) in enumerate(treads):
            nosing = [(xa, z), (xb + 0.02, z), (xb + 0.03, z + 0.01), (xb + 0.03, z + 0.02), (xb + 0.02, z + cover), (xa, z + cover)]
            below = z - rise + (cover if i else 0.0)
            parts += [profile_y(f, nosing, gap, width), box_solid(f, xb, gap, below, xb + 0.01, width, z)]
    s.add("IfcStair", "Treppe", parts, keys=(STAIR,), predefined_type="STRAIGHT_RUN_STAIR")
    return s


RAILING = "gelaender"


def railings(level: str) -> Scene:
    """hoch: as mitte, plus base plates screwed to the slab under the posts;
    mitte: handrail, bottom rail, posts and balusters at exact spacing; tief: one closed body from the slab to the handrail."""
    s = Scene.new("Gelaender")
    f = s.ifc_file
    w, d, h = 5.0, 3.0, 1.0
    _floor(s, 0.0, 0.0, w, d, name="Galerie")
    runs = (((0.0, d - 0.1), (w - 0.1, d - 0.1)), ((w - 0.1, d - 0.1), (w - 0.1, 0.0)))
    if level == TIEF:
        a, b = d - 0.1, w - 0.1
        t = 0.025
        plan = [(0.0, a - t), (b - t, a - t), (b - t, 0.0), (b + t, 0.0), (b + t, a + t), (0.0, a + t)]
        s.add("IfcRailing", "Gelaender", [prism(f, plan, 0.0, h)], keys=(RAILING,), predefined_type="GUARDRAIL")
        return s

    def rail(z: float, size: float) -> list[ifcopenshell.entity_instance]:
        (a, corner), (_, b) = runs
        return [
            duct_solid(f, (a[0], a[1], z), (corner[0] + size / 2, corner[1], z), size, size),
            duct_solid(f, (corner[0], corner[1], z), (b[0], b[1], z), size, size),
        ]

    parts = rail(h - 0.025, 0.05) + rail(0.12, 0.03)
    spacing, size = 0.12, 0.018
    balusters = set()
    for (ax, ay), (bx, by) in runs:
        length = abs(bx - ax) + abs(by - ay)
        for k in range(int(length / spacing) + 1):
            u = min(k * spacing, length) / length
            balusters.add((round(ax + (bx - ax) * u, 3), round(ay + (by - ay) * u, 3)))
    for x, y in sorted(balusters):
        parts.append(box_solid(f, x - size / 2, y - size / 2, 0.135, x + size / 2, y + size / 2, h - 0.05))
    plate, half, screw = 0.015, 0.075, 0.05
    base = plate if level == HOCH else 0.0
    # End posts sit inside the slab edge so the base plates do not overhang.
    for x, y in ((half, d - 0.1), (1.6, d - 0.1), (3.3, d - 0.1), (w - 0.1, d - 0.1), (w - 0.1, 1.5), (w - 0.1, half)):
        parts.append(box_solid(f, x - 0.025, y - 0.025, base, x + 0.025, y + 0.025, h - 0.05))
        if level == HOCH:
            parts.append(box_solid(f, x - half, y - half, 0.0, x + half, y + half, plate))
            parts += [vertical_cylinder_solid(f, x + dx, y + dy, plate, 0.011, 0.01, segments=8) for dx in (-screw, screw) for dy in (-screw, screw)]
    s.add("IfcRailing", "Gelaender", parts, keys=(RAILING,), predefined_type="GUARDRAIL")
    return s


RAMP = "rampe"


def ramps(level: str) -> Scene:
    """hoch: variable slope with landing, exact thickness; mitte: variable slope, straight soffit; tief: constant slope wedge."""
    s = Scene.new("Rampe")
    f = s.ifc_file
    length, width, rise = 6.0, 1.5, 1.2
    _floor(s, -1.2, -1.2, length + 0.6, width + 0.6)
    s.add("IfcSlab", "Podest", [box_solid(f, -1.2, -1.2, 0.0, 0.0, width + 0.6, rise)], predefined_type="LANDING")
    s.add("IfcWall", "Wand", [box_solid(f, -1.2, -1.2, 0.0, length + 0.6, -1.0, rise + 1.0)], predefined_type="SOLIDWALL")
    top = [(4.0, 0.45), (2.8, 0.45), (0.0, rise)]
    (x_land, z_land) = top[0]
    if level == HOCH:
        t = 0.2
        start = length - t * (length - x_land) / z_land
        section = [(length, 0.0), (start, 0.0), *((x, z - t) for x, z in top), *reversed(top)]
    elif level == MITTE:
        start = length - 0.2 * (length - x_land) / z_land
        section = [(length, 0.0), (start, 0.0), (0.0, rise - 0.45), *reversed(top)]
    else:
        start = length - 0.25 * length / rise
        section = [(length, 0.0), (start, 0.0), (0.0, rise - 0.25), (0.0, rise)]
    s.add("IfcRamp", "Rampe", [profile_y(f, section, 0.0, width)], keys=(RAMP,), predefined_type="STRAIGHT_RUN_RAMP")
    return s


FOOTING = "fundament"


def footings(level: str) -> Scene:
    """hoch: stepped strip and pad footings; mitte: simple boxes; tief: not modelled (ghost). Base slab dotted."""
    s = Scene.new("Fundamente")
    f = s.ifc_file
    w, d = 6.0, 4.0
    s.add("IfcSlab", "Bodenplatte", [box_solid(f, 0.0, 0.0, -0.3, w, d, 0.0)], predefined_type="BASESLAB", dotted=True)
    s.add("IfcWall", "Wand-Rueck", [box_solid(f, 0.0, 0.0, 0.0, w, 0.25, 1.0)], predefined_type="SOLIDWALL")
    s.add("IfcWall", "Wand-Seite", [box_solid(f, 0.0, 0.25, 0.0, 0.25, d, 1.0)], predefined_type="SOLIDWALL")
    s.add("IfcColumn", "Stuetze", [box_solid(f, 2.85, 1.85, 0.0, 3.15, 2.15, 1.0)], predefined_type="COLUMN")

    def strip(width: float, z0: float, z1: float) -> ifcopenshell.entity_instance:
        o = (width - 0.25) / 2
        return _cut(f, box_solid(f, -o, -o, z0, w + o, d + o, z1), box_solid(f, 0.25 + o, 0.25 + o, z0 - 0.1, w - 0.25 - o, d - 0.25 - o, z1 + 0.1))

    def pad(half: float, z0: float, z1: float) -> ifcopenshell.entity_instance:
        return box_solid(f, 3.0 - half, 2.0 - half, z0, 3.0 + half, 2.0 + half, z1)

    if level == HOCH:
        parts = [strip(0.9, -0.9, -0.6), strip(0.55, -0.6, -0.3), pad(0.7, -0.9, -0.6), pad(0.45, -0.6, -0.3)]
    else:
        parts = [strip(0.6, -0.8, -0.3), pad(0.6, -0.8, -0.3)]
    s.add("IfcFooting", "Fundamente", parts, keys=(FOOTING,), predefined_type="STRIP_FOOTING")
    if level == TIEF:
        s.volume(FOOTING)
    return s


# ---------------------------------------------------------------------------
# Interior
# ---------------------------------------------------------------------------

CEILING = "abgehaengte-decke"


def ceilings(level: str) -> Scene:
    """hoch: grid tiles with luminaires and hangers; mitte: one plate; tief: not modelled (ghost). Raw slab dotted."""
    s = Scene.new("Abgehaengte Decke")
    f = s.ifc_file
    w, d, zc = 5.0, 4.0, 2.6
    _floor(s, -0.2, -0.2, w, d)
    _back_walls(s, w, d, 3.0)
    _floor(s, -0.2, -0.2, w, d, 3.25, dotted=True, name="Rohdecke")
    if level == HOCH:
        nx, ny, gap = 8, 6, 0.012
        tx, ty = w / nx, d / ny
        lights = {(2, 2), (5, 3)}
        parts = [
            box_solid(f, i * tx + gap / 2, j * ty + gap / 2, zc, (i + 1) * tx - gap / 2, (j + 1) * ty - gap / 2, zc + 0.03)
            for i in range(nx)
            for j in range(ny)
            if (i, j) not in lights
        ]
        parts += [pipe_solid(f, (x, y, zc + 0.03), (x, y, 3.0), 0.008, segments=6) for x in (1.25, 2.5, 3.75) for y in (1.0, 2.0, 3.0)]
        for i, j in lights:
            s.add("IfcLightFixture", f"Leuchte-{i}-{j}", [box_solid(f, i * tx + gap, j * ty + gap, zc - 0.02, (i + 1) * tx - gap, (j + 1) * ty - gap, zc + 0.08)], predefined_type="DIRECTIONSOURCE")
    else:
        parts = [box_solid(f, 0.0, 0.0, zc, w, d, zc + 0.04)]
    s.add("IfcCovering", "Abgehaengte Decke", parts, keys=(CEILING,), predefined_type="CEILING")
    if level == TIEF:
        s.volume(CEILING)
    return s


FURNITURE = "moebel"


def furniture(level: str) -> Scene:
    """hoch: built-in wardrobe plus bunk bed; mitte: built-in wardrobe; tief: not modelled (ghost)."""
    s = Scene.new("Moebel")
    f = s.ifc_file
    w, d = 5.0, 4.0
    _floor(s, -0.2, -0.2, w, d)
    _back_walls(s, w, d, 2.6)
    wardrobe = [box_solid(f, 0.0, 0.0, 0.0, 2.4, 0.55, 0.1), box_solid(f, 0.0, 0.0, 0.1, 2.4, 0.6, 2.3)]
    wardrobe += [box_solid(f, i * 0.6 + 0.004, 0.6, 0.11, (i + 1) * 0.6 - 0.004, 0.62, 2.29) for i in range(4)]
    s.add("IfcFurniture", "Einbauschrank", wardrobe, keys=(FURNITURE,), predefined_type="USERDEFINED", object_type="Einbaumoebel")
    if level == HOCH:
        x0, x1, y0, y1 = 3.0, 4.0, 0.1, 2.1
        bed = [box_solid(f, x - 0.025, y - 0.025, 0.0, x + 0.025, y + 0.025, 1.75) for x in (x0, x1) for y in (y0, y1)]
        for z in (0.3, 1.3):
            bed += [box_solid(f, x0, y0, z, x1, y1, z + 0.12), box_solid(f, x0 + 0.03, y0 + 0.03, z + 0.12, x1 - 0.03, y1 - 0.03, z + 0.26)]
        bed.append(box_solid(f, x1 - 0.02, y0 + 0.6, 1.62, x1 + 0.0, y1, 1.7))
        bed += [box_solid(f, x1, y, 0.0, x1 + 0.03, y + 0.03, 1.75) for y in (1.4, 1.8)]
        bed += [box_solid(f, x1, 1.43, z, x1 + 0.03, 1.8, z + 0.025) for z in (0.6, 0.9, 1.15, 1.5)]
        s.add("IfcFurniture", "Etagenbett", bed, keys=(FURNITURE,), predefined_type="BED")
    if level == TIEF:
        s.volume(FURNITURE)
    return s


FLOOR_BUILDUP = "bodenaufbau"


def floor_buildups(level: str) -> Scene:
    """hoch: two floor finishes in one room, separated by an open joint; mitte: one covering over the whole room;
    tief: no covering, the information sits on the room."""
    s = Scene.new("Bodenaufbauten")
    f = s.ifc_file
    w, d, xs, joint = 6.0, 4.0, 3.6, 0.08
    s.add("IfcSlab", "Rohdecke", [box_solid(f, -0.2, -0.2, -0.25, w, d, 0.0)], predefined_type="FLOOR")
    _back_walls(s, w, d, 2.6)
    if level == TIEF:
        s.add("IfcSpace", "Raum", [box_solid(f, 0.0, 0.0, 0.0, w, d, 2.6)], keys=(FLOOR_BUILDUP,), predefined_type="SPACE")
        s.volume(FLOOR_BUILDUP)
        return s
    if level == MITTE:
        s.add("IfcCovering", "Bodenbelag", [box_solid(f, 0.0, 0.0, 0.0, w, d, 0.15)], keys=(FLOOR_BUILDUP,), predefined_type="FLOORING")
        return s
    s.add("IfcCovering", "Parkett", [box_solid(f, 0.0, 0.0, 0.0, xs - joint / 2, d, 0.15)], keys=(FLOOR_BUILDUP,), predefined_type="FLOORING")
    s.add("IfcCovering", "Platten", [box_solid(f, xs + joint / 2, 0.0, 0.0, w, d, 0.15)], keys=(FLOOR_BUILDUP,), predefined_type="FLOORING")
    return s


ROOM = "raum"


def _room_volume(level: str, x0: float, x1: float, d: float, z0: float, z1: float, beam: tuple[float, float, float]) -> list[tuple[float, float]] | None:
    """Section (x, z) of a space: hoch follows the slab soffit and the beam recess, mitte a plain box
    up to the beam underside, tief a flat footprint."""
    b0, b1, bz = beam
    if level == HOCH:
        return [(x0, z0), (x1, z0), (x1, z1), (b1, z1), (b1, bz), (b0, bz), (b0, z1), (x0, z1)]
    if level == MITTE:
        return [(x0, z0), (x1, z0), (x1, bz), (x0, bz)]
    return [(x0, z0), (x1, z0), (x1, z0 + 0.3), (x0, z0 + 0.3)]


def rooms(level: str) -> Scene:
    """hoch: space up to the slab soffit with beam recess; mitte: plain box up to the beam; tief: flat footprint."""
    s = Scene.new("Innenraum")
    f = s.ifc_file
    w, d, h = 5.0, 4.0, 3.0
    _floor(s, -0.2, -0.2, w, d)
    _back_walls(s, w, d, h)
    _floor(s, -0.2, -0.2, w, d, h + 0.25, dotted=True, name="Rohdecke")
    beam = (2.3, 2.7, 2.6)
    s.add("IfcBeam", "Unterzug", [box_solid(f, beam[0], 0.0, beam[2], beam[1], d, h)], predefined_type="BEAM")
    s.add("IfcSpace", "Raum", [profile_y(f, _room_volume(level, 0.0, w, d, 0.0, h, beam), 0.0, d)], keys=(ROOM,), predefined_type="SPACE")
    s.volume(ROOM)
    return s


AIR_SPACE = "luftraum"


def air_spaces(level: str) -> Scene:
    """Two-storey hall: the upper storey part of the void is the Luftraum, the gallery and ground floor room are context."""
    s = Scene.new("Luftraum")
    f = s.ifc_file
    w, d, h = 6.0, 4.0, 3.2
    xg = 2.0
    _floor(s, -0.2, -0.2, w, d)
    _floor(s, -0.2, -0.2, xg, d, h, name="Galerie")
    _back_walls(s, w, d, 2 * h)
    _floor(s, -0.2, -0.2, w, d, 2 * h + 0.25, dotted=True, name="Dach")
    s.add("IfcSpace", "Halle-EG", [box_solid(f, 0.0, 0.0, 0.0, w, d, h - 0.25)], predefined_type="SPACE")
    beam = (3.8, 4.2, 2 * h - 0.4)
    s.add("IfcBeam", "Unterzug", [box_solid(f, beam[0], 0.0, beam[2], beam[1], d, 2 * h)], predefined_type="BEAM")
    s.add("IfcSpace", "Luftraum", [profile_y(f, _room_volume(level, xg, w, d, h, 2 * h, beam), 0.0, d)], keys=(AIR_SPACE,), predefined_type="SPACE")
    s.volume(AIR_SPACE)
    return s


# Bestand element family → (scene builder, accented key).
_FAMILIES = {
    "wande": (walls, WALL),
    "fenster-oberlichter": (windows, WINDOW),
    "tur-tor-revisionsoffnung": (doors, DOOR),
    "fassade": (facade, FACADE),
    "dach": (roofs, ROOF),
    "decken-flachdacher": (slabs, SLAB),
    "stutzen": (columns, COLUMN),
    "unter-uberzuge": (beams, BEAM),
    "treppe": (stairs, STAIR),
    "gelander": (railings, RAILING),
    "rampe": (ramps, RAMP),
    "fundamente": (footings, FOOTING),
    "abgehangte-decke": (ceilings, CEILING),
    "mobel": (furniture, FURNITURE),
    "bodenaufbauten": (floor_buildups, FLOOR_BUILDUP),
    "innenraum": (rooms, ROOM),
    "luftraum": (air_spaces, AIR_SPACE),
}

# Families framed from the side so their section profile (or beam web) reads.
_CAMERA_DIRECTIONS = {"rampe": (0.3, 1.0, 0.2), "unter-uberzuge": (0.45, 1.0, 0.3), "treppe": (0.35, 1.0, 0.25)}

LOD_CARDS: dict[str, Card] = {
    f"{family}-{level}": Card(build, key, {"level": level}, camera_padding=1.3, camera_direction=_CAMERA_DIRECTIONS.get(family))
    for family, (build, key) in _FAMILIES.items()
    for level in LEVELS
}

def lod_level(card_id: str) -> tuple[str, str] | None:
    """``(family, level)`` of a detail-level card id (``wande-hoch`` → ``("wande", "hoch")``), else None."""
    family, _, level = card_id.rpartition("-")
    return (family, level) if level in LEVELS and family in _FAMILIES else None


def lod_set(family: str) -> list[tuple[str, Card]]:
    """The levels of one family, rendered together at one scale."""
    return [(level, LOD_CARDS[f"{family}-{level}"]) for level in LEVELS]
