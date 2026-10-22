"""Transport installations: slope railways (funicular, winch railway, monorack), tunnel railway,
stair lift, escalator, moving walkway and cableways (aerial, material, target).

Camera from +X/+Y; slopes fall towards +X.
"""

from __future__ import annotations

import math

from generators.mep_parts import box_solid, pipe_solid, vertical_cylinder_solid
from generators.parts import rect_polyline
from generators.slab import add_slab
from generators.structural_core import extrude_with_voids

from dataschema.geometry import profile_x, profile_y
from dataschema.scene import Scene
from dataschema.scenes_rooms import corner_room, horizontal_cylinder, polyline_solids

FUNICULAR = "d12-01-002-standseilbahnen"
WINCH_RAILWAY = "d12-01-003-windenbahnen"
MONORACK = "d12-01-004-monorak"
TUNNEL_RAILWAY = "d12-01-005-stollenbahn"
STAIR_LIFT = "d12-03-001-treppenaufzug"
ESCALATOR = "d12-04-001-fahrtreppe"
MOVING_WALKWAY = "d12-05-001-fahrsteig"
AERIAL_ROPEWAY = "i05-07-001-luftseilbahnen"
MATERIAL_ROPEWAY = "i05-07-002-materialseilbahnen"
TARGET_ROPEWAY = "i05-07-003-zielseilbahn"
MANUAL_CRANE = "d12-06-004-krananlagen-handbetrieben"
VEHICLE_LIFT = "d12-06-001-hebeeinrichtung"


def _slope(s: Scene, length: float, rise: float, width: float, top: float = 4.0, bottom: float = 4.0):
    """Hillside falling towards +X from ``rise`` at x = 0 to 0 at x = ``length``; returns z(x)."""
    polygon = [(-top, -0.4), (length + bottom, -0.4), (length + bottom, 0.0), (length, 0.0), (0.0, rise), (-top, rise)]
    s.add("IfcGeographicElement", "Gelaende", [profile_y(s.ifc_file, polygon, 0.0, width)], predefined_type="TERRAIN")

    def z(x: float) -> float:
        return rise * min(max(1.0 - x / length, 0.0), 1.0)

    return z


def _catenary(a, b, sag: float, n: int = 12) -> list:
    return [
        (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n, a[2] + (b[2] - a[2]) * i / n - sag * 4 * (i / n) * (1 - i / n))
        for i in range(n + 1)
    ]


def _on_slope(s: Scene, name: str, z, x0: float, x1: float, y0: float, y1: float, lift: float, height: float, keys=(), ifc_class="IfcBuildingElementProxy", **kwargs):
    """Body standing on the slope: parallelogram side profile ``lift`` .. ``lift + height`` above ground."""
    polygon = [(x0, z(x0) + lift), (x1, z(x1) + lift), (x1, z(x1) + lift + height), (x0, z(x0) + lift + height)]
    return s.add(ifc_class, name, [profile_y(s.ifc_file, polygon, y0, y1)], keys=keys, **kwargs)


def _sleepers(f, z, x0: float, x1: float, y0: float, y1: float, spacing: float = 0.8) -> list:
    solids = []
    x = x0
    while x < x1:
        zc = z(x + 0.1)
        solids.append(box_solid(f, x, y0, zc - 0.05, x + 0.2, y1, zc + 0.08))
        x += spacing
    return solids


# ---------------------------------------------------------------------------
# Slope railways
# ---------------------------------------------------------------------------


def slope_railway(kind: str = "funicular") -> Scene:
    """Hillside with a rail-bound system: ``funicular`` (stepped car on a haul rope with drive at the top),
    ``winch`` (platform car on a narrow track pulled by a winch house) or ``monorack`` (single rack rail
    on posts with tractor and trailer)."""
    s = Scene.new("Hangbahn", storey_name="Terrain")
    f = s.ifc_file
    length, rise, width = 14.0, 6.5, 7.0
    z = _slope(s, length, rise, width)
    cy = width / 2

    if kind == "funicular":
        keys = (FUNICULAR,)
        g = 0.6
        s.add("IfcBuildingElementProxy", "Schwellen", _sleepers(f, z, 0.4, length + 2.0, cy - 0.9, cy + 0.9), keys=keys, object_type="Schwelle", thin=True)
        s.add("IfcBuildingElementProxy", "Schienen", [pipe_solid(f, (-0.5, cy + d, z(-0.5) + 0.12), (0.0, cy + d, rise + 0.12), 0.05, segments=8) for d in (-g, g)] + [pipe_solid(f, (0.0, cy + d, rise + 0.12), (length, cy + d, 0.12), 0.05, segments=8) for d in (-g, g)] + [pipe_solid(f, (length, cy + d, 0.12), (length + 2.0, cy + d, 0.12), 0.05, segments=8) for d in (-g, g)], keys=keys, object_type="Schiene", thin=True)
        # Stepped car: three compartments following the gradient.
        x0 = 6.0
        parts = []
        for i in range(3):
            xa = x0 + i * 1.4
            zb = z(xa + 1.4) + 0.5
            parts.append(box_solid(f, xa, cy - 1.1, zb, xa + 1.4, cy + 1.1, zb + 2.3))
        s.add("IfcTransportElement", "Standseilbahnwagen", parts, predefined_type="USERDEFINED", object_type="Standseilbahnwagen")
        s.add("IfcBuildingElementProxy", "Fenster", [box_solid(f, x0 + i * 1.4 + 0.15, cy + 1.1, z(x0 + i * 1.4 + 1.4) + 1.6, x0 + i * 1.4 + 1.25, cy + 1.13, z(x0 + i * 1.4 + 1.4) + 2.5) for i in range(3)], object_type="Fenster")
        s.add("IfcBuildingElementProxy", "Zugseil", [pipe_solid(f, (-1.0, cy, rise + 0.2), (x0, cy, z(x0) + 0.25), 0.04, segments=6)], keys=keys, object_type="Zugseil", thin=True)
        s.add("IfcBuildingElementProxy", "Seilrollen", [horizontal_cylinder(f, x - 0.05, x + 0.05, cy, z(x) + 0.12, 0.1, segments=10) for x in (1.5, 3.0, 4.5)], keys=keys, object_type="Seilrolle", thin=True)
        # Top station: open drive hall with bull wheel.
        s.add("IfcColumn", "Bergstation-Stuetzen", [box_solid(f, x, y, rise, x + 0.25, y + 0.25, rise + 3.4) for x in (-3.8, -0.4) for y in (0.4, width - 0.65)], keys=keys, predefined_type="COLUMN")
        s.add("IfcRoof", "Bergstation-Dach", [box_solid(f, -4.0, 0.2, rise + 3.4, 0.1, width - 0.2, rise + 3.7)], keys=keys, predefined_type="FLAT_ROOF")
        s.add("IfcElectricMotor", "Antrieb", [box_solid(f, -3.4, cy - 2.4, rise, -2.0, cy - 1.2, rise + 1.2)], keys=keys)
        s.add("IfcBuildingElementProxy", "Seilscheibe", [vertical_cylinder_solid(f, -2.0, cy, rise + 0.1, 1.0, 0.15, segments=24), vertical_cylinder_solid(f, -2.0, cy, rise, 0.2, 0.1, segments=12)], keys=keys, object_type="Seilscheibe")
        s.add("IfcBuildingElementProxy", "Bahnsteig", [box_solid(f, length, cy + 1.3, 0.0, length + 3.5, width - 0.2, 0.6)], keys=keys, object_type="Bahnsteig")
    elif kind == "winch":
        keys = (WINCH_RAILWAY,)
        g = 0.4
        s.add("IfcBuildingElementProxy", "Schwellen", _sleepers(f, z, 0.3, length + 1.0, cy - 0.6, cy + 0.6, spacing=0.9), keys=keys, object_type="Schwelle", thin=True)
        s.add("IfcBuildingElementProxy", "Schienen", [pipe_solid(f, (0.0, cy + d, rise + 0.1), (length, cy + d, 0.1), 0.04, segments=8) for d in (-g, g)] + [pipe_solid(f, (length, cy + d, 0.1), (length + 1.0, cy + d, 0.1), 0.04, segments=8) for d in (-g, g)], keys=keys, object_type="Schiene", thin=True)
        x0, x1 = 7.0, 9.0
        _on_slope(s, "Plattformwagen", z, x0, x1, cy - 0.8, cy + 0.8, 0.3, 0.12, ifc_class="IfcTransportElement", predefined_type="USERDEFINED", object_type="Plattformwagen")
        _on_slope(s, "Gelaender", z, x0, x0 + 0.06, cy - 0.8, cy + 0.8, 0.42, 0.9, object_type="Stirnwand")
        s.add("IfcBuildingElementProxy", "Ladung", [box_solid(f, 7.6, cy - 0.5, z(8.4) + 0.42, 8.4, cy + 0.5, z(8.4) + 1.2)], object_type="Ladung")
        # Winch house at the top with drum and rope.
        s.add("IfcWall", "Windenhaus", [box_solid(f, -3.6, cy - 1.6, rise, -0.8, cy - 1.4, rise + 2.4), box_solid(f, -3.6, cy + 1.4, rise, -0.8, cy + 1.6, rise + 2.4), box_solid(f, -3.8, cy - 1.6, rise, -3.6, cy + 1.6, rise + 2.4)], keys=keys, predefined_type="SOLIDWALL")
        s.add("IfcRoof", "Windenhaus-Dach", [box_solid(f, -3.9, cy - 1.8, rise + 2.4, -0.6, cy + 1.8, rise + 2.6)], keys=keys, predefined_type="FLAT_ROOF")
        s.add("IfcBuildingElementProxy", "Seilwinde", [horizontal_cylinder(f, -2.2, -1.8, cy, rise + 0.7, 0.45, segments=20), pipe_solid(f, (-2.0, cy - 0.7, rise + 0.7), (-2.0, cy + 0.7, rise + 0.7), 0.4, segments=20), box_solid(f, -3.4, cy - 0.5, rise, -2.4, cy + 0.5, rise + 0.9)], keys=keys, object_type="Seilwinde")
        s.add("IfcBuildingElementProxy", "Zugseil", [pipe_solid(f, (-2.0, cy, rise + 0.3), (x0, cy, z(x0) + 0.45), 0.03, segments=6)], keys=keys, object_type="Zugseil", thin=True)
    elif kind == "monorack":
        keys = (MONORACK,)
        posts = []
        x = 0.3
        while x < length + 1.5:
            posts.append(box_solid(f, x - 0.04, cy - 0.04, z(x) - 0.1, x + 0.04, cy + 0.04, z(x) + 0.4))
            x += 1.2
        s.add("IfcBuildingElementProxy", "Stuetzen", posts, keys=keys, object_type="Schienenstuetze", thin=True)
        s.add("IfcBuildingElementProxy", "Zahnschiene", [pipe_solid(f, (0.0, cy, rise + 0.45), (length, cy, 0.45), 0.06, segments=4), pipe_solid(f, (length, cy, 0.45), (length + 1.5, cy, 0.45), 0.06, segments=4)], keys=keys, object_type="Zahnschiene", thin=True)
        _on_slope(s, "Triebwagen", z, 4.0, 5.2, cy - 0.45, cy + 0.45, 0.5, 0.8, ifc_class="IfcTransportElement", predefined_type="USERDEFINED", object_type="Monorak-Triebwagen")
        s.add("IfcFurniture", "Sitz", [box_solid(f, 4.3, cy - 0.25, z(4.6) + 1.3, 4.9, cy + 0.25, z(4.6) + 1.4), box_solid(f, 4.3, cy - 0.25, z(4.3) + 1.4, 4.38, cy + 0.25, z(4.3) + 2.0)], predefined_type="CHAIR")
        _on_slope(s, "Anhaenger", z, 5.5, 7.5, cy - 0.6, cy + 0.6, 0.55, 0.1, ifc_class="IfcTransportElement", predefined_type="USERDEFINED", object_type="Monorak-Anhaenger")
        s.add("IfcBuildingElementProxy", "Kisten", [box_solid(f, x, cy - 0.45, z(x + 0.3) + 0.65, x + 0.6, cy + 0.45, z(x + 0.3) + 1.1) for x in (5.7, 6.6)], object_type="Kiste")
        s.add("IfcBuildingElementProxy", "Rebstoecke", [box_solid(f, x, y, z(x) - 0.1, x + 0.06, y + 0.06, z(x) + 1.4) for x in (1.0, 3.0, 5.0, 7.0, 9.0, 11.0) for y in (1.2, 2.2, width - 2.2, width - 1.2)], object_type="Rebstock", thin=True)
    else:
        raise ValueError(f"unknown slope railway {kind!r}")
    return s


# ---------------------------------------------------------------------------
# Stollenbahn
# ---------------------------------------------------------------------------


def tunnel_railway() -> Scene:
    """Tunnel cut open towards the camera: invert, back wall and half vault; narrow-gauge track with
    a battery locomotive and two mine cars, lights along the vault."""
    s = Scene.new("Stollen", storey_name="Stollen")
    f = s.ifc_file
    length, r, cy, spring = 14.0, 2.2, 2.4, 1.4
    s.add("IfcSlab", "Sohle", [box_solid(f, 0.0, cy - r - 0.3, -0.3, length, cy + r, 0.0)], predefined_type="BASESLAB")
    s.add("IfcWall", "Ulme", [box_solid(f, 0.0, cy - r - 0.3, 0.0, length, cy - r, spring)], predefined_type="SOLIDWALL")
    shell = [(cy + (r + 0.3) * math.cos(math.radians(a)), spring + (r + 0.3) * math.sin(math.radians(a))) for a in range(180, 79, -10)]
    shell += [(cy + r * math.cos(math.radians(a)), spring + r * math.sin(math.radians(a))) for a in range(80, 181, 10)]
    s.add("IfcBuildingElementProxy", "Gewoelbe", [profile_x(f, list(reversed(shell)), 0.0, length)], object_type="Tunnelschale")
    s.add("IfcLightFixture", "Stollenleuchten", [box_solid(f, x, cy - r + 0.1, 2.6, x + 0.6, cy - r + 0.3, 2.75) for x in (2.0, 7.0, 12.0)], predefined_type="DIRECTIONSOURCE")

    keys = (TUNNEL_RAILWAY,)
    ty = cy + 0.2
    s.add("IfcBuildingElementProxy", "Schwellen", [box_solid(f, x, ty - 0.55, 0.0, x + 0.15, ty + 0.55, 0.1) for x in [0.2 + 0.7 * i for i in range(20)]], keys=keys, object_type="Schwelle", thin=True)
    s.add("IfcBuildingElementProxy", "Schienen", [box_solid(f, 0.0, ty + d - 0.03, 0.1, length, ty + d + 0.03, 0.2) for d in (-0.3, 0.3)], keys=keys, object_type="Schiene", thin=True)
    s.add(
        "IfcTransportElement",
        "Akkulok",
        [box_solid(f, 2.0, ty - 0.5, 0.3, 4.2, ty + 0.5, 1.3), box_solid(f, 2.0, ty - 0.5, 1.3, 2.9, ty + 0.5, 2.0), box_solid(f, 2.0, ty - 0.5, 2.0, 3.1, ty + 0.5, 2.06)]
        + [pipe_solid(f, (x, ty - 0.45, 0.32), (x, ty + 0.45, 0.32), 0.2, segments=14) for x in (2.5, 3.7)],
        predefined_type="USERDEFINED",
        object_type="Akkulokomotive",
    )
    cars = []
    for x0 in (4.6, 6.8):
        cars.append(box_solid(f, x0, ty - 0.5, 0.45, x0 + 1.8, ty + 0.5, 1.4))
        cars.extend(pipe_solid(f, (x, ty - 0.45, 0.3), (x, ty + 0.45, 0.3), 0.17, segments=12) for x in (x0 + 0.4, x0 + 1.4))
    s.add("IfcTransportElement", "Rollwagen", cars, predefined_type="USERDEFINED", object_type="Rollwagen")
    return s


# ---------------------------------------------------------------------------
# Treppenaufzug
# ---------------------------------------------------------------------------


def stair_lift() -> Scene:
    """Straight stair along the back wall rising towards -X onto a landing in the corner; lift rail on the
    wall side of the treads, chair parked at the foot over the walking line, facing across the stair."""
    s = corner_room("Treppenhaus", width=7.0, depth=4.0, height=4.4)
    f = s.ifc_file
    n, rise, going, w, d = 16, 0.175, 0.28, 1.2, 0.25
    h = n * rise
    xl = 1.3
    xf = xl + (n - 1) * going

    def nosing(x: float) -> float:
        return min(max((xf + going - x) * rise / going, 0.0), h)

    def tread(x: float) -> float:
        return 0.0 if x > xf else min(math.floor((xf - x) / going) + 1, n) * rise

    profile = [(xf, 0.0)]
    for i in range(n):
        profile += [(xf - i * going, (i + 1) * rise), (max(xf - (i + 1) * going, xl), (i + 1) * rise)]
    profile += [(xl, h - d), (xf + going - d * going / rise, 0.0)]
    s.add("IfcStairFlight", "Treppenlauf", [profile_y(f, profile, 0.0, w)], predefined_type="STRAIGHT")
    s.add("IfcSlab", "Podest", [box_solid(f, 0.0, 0.0, h - d, xl, w, h)], predefined_type="LANDING")
    gy = w - 0.04
    posts = [box_solid(f, x - 0.02, gy - 0.02, tread(x), x + 0.02, gy + 0.02, nosing(x) + 0.9) for x in (xf - 0.14, xf - 5 * going - 0.14, xf - 10 * going - 0.14, xl + 0.1)]
    s.add("IfcRailing", "Gelaender", posts + [pipe_solid(f, (xf - 0.14, gy, nosing(xf - 0.14) + 0.9), (xl + 0.1, gy, h + 0.9), 0.025, segments=8)], predefined_type="GUARDRAIL", thin=True)

    keys = (STAIR_LIFT,)
    ry, lift = 0.15, 0.35
    rail = [(xf + 0.8, ry, lift), (xf + going, ry, lift), (xl, ry, h + lift), (xl - 0.6, ry, h + lift)]
    s.add("IfcBuildingElementProxy", "Fahrschiene", polyline_solids(f, rail, 0.045, segments=10), keys=keys, object_type="Treppenliftschiene", thin=True)
    supports = (xf + 0.65, xf - 4 * going - 0.14, xf - 10 * going - 0.14, xl - 0.4)
    s.add("IfcBuildingElementProxy", "Schienenstuetzen", [box_solid(f, x - 0.03, ry - 0.03, tread(x), x + 0.03, ry + 0.03, nosing(x) + lift) for x in supports], keys=keys, object_type="Schienenstuetze", thin=True)
    cx = xf + 0.35
    s.add(
        "IfcTransportElement",
        "Treppenliftsitz",
        [
            box_solid(f, cx - 0.2, ry - 0.1, 0.15, cx + 0.2, ry + 0.12, 0.6),
            box_solid(f, cx - 0.25, ry + 0.12, 0.6, cx + 0.25, ry + 0.24, 1.25),
            box_solid(f, cx - 0.25, ry + 0.12, 0.5, cx + 0.25, ry + 0.6, 0.6),
            box_solid(f, cx - 0.27, ry + 0.24, 0.75, cx - 0.2, ry + 0.6, 0.8),
            box_solid(f, cx + 0.2, ry + 0.24, 0.75, cx + 0.27, ry + 0.6, 0.8),
            box_solid(f, cx - 0.05, ry + 0.12, 0.06, cx + 0.05, ry + 0.2, 0.5),
            box_solid(f, cx - 0.2, ry + 0.2, 0.06, cx + 0.2, ry + 0.55, 0.1),
        ],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Treppenliftsitz",
    )
    s.add("IfcSwitchingDevice", "Rufstationen", [box_solid(f, xf + 1.3, 0.0, 1.0, xf + 1.42, 0.04, 1.15), box_solid(f, 0.0, 0.6, h + 1.0, 0.04, 0.72, h + 1.15)], keys=keys, predefined_type="MOMENTARYSWITCH")
    return s


# ---------------------------------------------------------------------------
# Handbetriebener Kran
# ---------------------------------------------------------------------------


def _i_beam(f, axis: str, a0: float, a1: float, c: float, z0: float, h: float, b: float, tf: float = 0.03, tw: float = 0.025) -> list:
    """I-profile along ``axis`` ("x" or "y") from ``a0`` to ``a1``, centred on ``c`` across the axis."""
    parts = [(c - b / 2, z0, c + b / 2, z0 + tf), (c - tw / 2, z0 + tf, c + tw / 2, z0 + h - tf), (c - b / 2, z0 + h - tf, c + b / 2, z0 + h)]
    if axis == "x":
        return [box_solid(f, a0, lo, za, a1, hi, zb) for lo, za, hi, zb in parts]
    return [box_solid(f, lo, a0, za, hi, a1, zb) for lo, za, hi, zb in parts]


def manual_crane() -> Scene:
    """Workshop with a hand-operated single-girder crane: runways on back-wall consoles and two steel
    columns, bridge pushed on end carriages, push trolley with a hand chain hoist whose hand chain loop
    hangs down to operator height; a motor on slings is lowered onto a machine base."""
    width, depth, height = 7.0, 5.0, 4.5
    s = corner_room("Werkstatt", width=width, depth=depth, height=height)
    f = s.ifc_file
    keys = (MANUAL_CRANE,)
    ry, rz, rh = (0.45, 4.5), 3.2, 0.3
    bx, yt = 3.6, 1.7

    s.add("IfcColumn", "Kranbahnstuetzen", [box_solid(f, x - 0.1, ry[1] - 0.1, 0.0, x + 0.1, ry[1] + 0.1, rz) for x in (0.4, 6.6)], predefined_type="COLUMN")
    s.add("IfcBuildingElementProxy", "Wandkonsolen", [box_solid(f, x - 0.08, 0.0, rz - 0.25, x + 0.08, ry[0] + 0.1, rz) for x in (0.8, 3.5, 6.2)], keys=keys, object_type="Kranbahnkonsole")
    s.add("IfcBeam", "Kranbahnen", [part for y in ry for part in _i_beam(f, "x", 0.0, width, y, rz, rh, 0.2)], keys=keys, predefined_type="USERDEFINED", object_type="Kranbahntraeger")

    zc = rz + rh
    carriages = [box_solid(f, bx - 0.7, y - 0.09, zc + 0.04, bx + 0.7, y + 0.09, zc + 0.18) for y in ry]
    carriages += [pipe_solid(f, (x, y - 0.11, zc + 0.08), (x, y + 0.11, zc + 0.08), 0.08, segments=14) for x in (bx - 0.5, bx + 0.5) for y in ry]
    s.add("IfcBuildingElementProxy", "Kopftraeger", carriages, keys=keys, object_type="Kopftraeger")
    zg = zc + 0.18
    s.add("IfcBeam", "Kranbruecke", _i_beam(f, "y", ry[0] - 0.1, ry[1] + 0.1, bx, zg, 0.32, 0.18), keys=keys, predefined_type="USERDEFINED", object_type="Eintraegerbruecke")

    s.add(
        "IfcBuildingElementProxy",
        "Rollfahrwerk",
        [
            box_solid(f, bx - 0.13, yt - 0.17, zg - 0.22, bx - 0.11, yt + 0.17, zg + 0.08),
            box_solid(f, bx + 0.11, yt - 0.17, zg - 0.22, bx + 0.13, yt + 0.17, zg + 0.08),
            box_solid(f, bx - 0.13, yt - 0.05, zg - 0.26, bx + 0.13, yt + 0.05, zg - 0.2),
            box_solid(f, bx - 0.03, yt - 0.03, zg - 0.36, bx + 0.03, yt + 0.03, zg - 0.26),
        ],
        keys=keys,
        object_type="Rollfahrwerk",
    )
    zh = zg - 0.55
    s.add(
        "IfcBuildingElementProxy",
        "Handkettenzug",
        [
            pipe_solid(f, (bx, yt - 0.18, zh), (bx, yt + 0.18, zh), 0.16, segments=20),
            pipe_solid(f, (bx, yt + 0.2, zh), (bx, yt + 0.27, zh), 0.22, segments=24),
        ],
        keys=keys,
        object_type="Handkettenzug",
    )
    loop_y, loop_z = yt + 0.235, 0.8
    s.add(
        "IfcBuildingElementProxy",
        "Handkette",
        polyline_solids(f, [(bx - 0.2, loop_y, zh), (bx - 0.2, loop_y, loop_z), (bx + 0.2, loop_y, loop_z), (bx + 0.2, loop_y, zh)], 0.018, segments=6),
        keys=keys,
        object_type="Handkette",
        thin=True,
    )
    zk = 1.95
    s.add("IfcBuildingElementProxy", "Lastkette", [pipe_solid(f, (bx, yt, zh - 0.16), (bx, yt, zk + 0.3), 0.018, segments=6)], keys=keys, object_type="Lastkette", thin=True)
    s.add(
        "IfcBuildingElementProxy",
        "Unterflasche",
        [box_solid(f, bx - 0.08, yt - 0.06, zk + 0.1, bx + 0.08, yt + 0.06, zk + 0.3), pipe_solid(f, (bx, yt, zk + 0.1), (bx, yt, zk), 0.025, segments=8)],
        keys=keys,
        object_type="Lasthaken",
    )

    zl = 1.4
    s.add("IfcBuildingElementProxy", "Anschlagmittel", [pipe_solid(f, (bx, yt, zk), (bx + dx, yt, zl + 0.2), 0.012, segments=6) for dx in (-0.3, 0.3)], object_type="Anschlagkette", thin=True)
    s.add("IfcElectricMotor", "Ladung", [horizontal_cylinder(f, bx - 0.4, bx + 0.4, yt, zl, 0.2, segments=20), box_solid(f, bx - 0.3, yt - 0.18, zl - 0.25, bx + 0.3, yt + 0.18, zl - 0.15)])
    s.add("IfcBuildingElementProxy", "Maschinensockel", [box_solid(f, bx - 0.6, yt - 0.45, 0.0, bx + 0.6, yt + 0.45, 0.6)], object_type="Maschinensockel")

    legs = [box_solid(f, x, y, 0.0, x + 0.05, y + 0.05, 0.85) for x in (4.85, 6.5) for y in (0.2, 0.8)]
    s.add("IfcFurniture", "Werkbank", [box_solid(f, 4.8, 0.15, 0.85, 6.6, 0.9, 0.9), *legs], predefined_type="TABLE")
    s.add("IfcBuildingElementProxy", "Palette", [box_solid(f, 0.8, 2.6, 0.0, 2.0, 3.4, 0.14)], object_type="Palette")
    s.add("IfcBuildingElementProxy", "Kisten", [box_solid(f, 0.9, 2.7, 0.14, 1.4, 3.3, 0.6), box_solid(f, 1.45, 2.7, 0.14, 1.9, 3.3, 0.5)], object_type="Kiste")
    return s


# ---------------------------------------------------------------------------
# Hebeeinrichtung
# ---------------------------------------------------------------------------


def vehicle_lift() -> Scene:
    """Workshop with a two-post vehicle lift: posts on base plates joined by an overhead bar with the
    hydraulic hose, carriages with four swing arms whose pads hold a car at working height; hydraulic
    power unit and control box on the back post, workbench and tyre stack as context."""
    width, depth, height = 8.0, 6.0, 4.6
    s = corner_room("Werkstatt", width=width, depth=depth, height=height)
    f = s.ifc_file
    keys = (VEHICLE_LIFT,)
    px, cy, gap = 4.0, 3.2, 1.55
    posts_y = (cy - gap, cy + gap)
    top = 4.1

    s.add("IfcBuildingElementProxy", "Bodenplatten", [box_solid(f, px - 0.3, y - 0.25, 0.0, px + 0.3, y + 0.25, 0.03) for y in posts_y], keys=keys, object_type="Fussplatte", thin=True)
    s.add(
        "IfcTransportElement",
        "Hebebuehne",
        [box_solid(f, px - 0.16, y - 0.14, 0.03, px + 0.16, y + 0.14, top) for y in posts_y]
        + [box_solid(f, px - 0.12, posts_y[0] - 0.1, top, px + 0.12, posts_y[1] + 0.1, top + 0.18)],
        keys=keys,
        predefined_type="LIFTINGGEAR",
        object_type="2-Saeulen-Hebebuehne",
    )
    s.add("IfcBuildingElementProxy", "Hydraulikleitung", polyline_solids(f, [(px - 0.2, posts_y[0], 1.2), (px - 0.2, posts_y[0], top + 0.08), (px - 0.2, posts_y[1], top + 0.08), (px - 0.2, posts_y[1], 1.2)], 0.02, segments=6), keys=keys, object_type="Hydraulikschlauch", thin=True)

    zr = 1.75
    za = zr + 0.08
    carriages = [box_solid(f, px - 0.22, y - 0.2, za - 0.25, px + 0.22, y + 0.2, za + 0.45) for y in posts_y]
    s.add("IfcBuildingElementProxy", "Hubschlitten", carriages, keys=keys, object_type="Hubschlitten")
    pads = [(px + dx, y) for dx in (-1.25, 1.1) for y in (cy - 0.72, cy + 0.72)]
    arms = []
    for x, y in pads:
        yp = posts_y[0] if y < cy else posts_y[1]
        arms.append(pipe_solid(f, (px, yp, za), (x, y, za), 0.06, segments=4))
        arms.append(vertical_cylinder_solid(f, x, y, za, 0.1, 0.17, segments=32))
    s.add("IfcBuildingElementProxy", "Tragarme", arms, keys=keys, object_type="Schwenkarm mit Teller")
    s.add("IfcElectricMotor", "Hydraulikaggregat", [box_solid(f, px - 0.25, posts_y[1] + 0.14, 0.7, px + 0.25, posts_y[1] + 0.55, 1.3), vertical_cylinder_solid(f, px, posts_y[1] + 0.35, 1.3, 0.15, 0.3, segments=32)], keys=keys)
    s.add("IfcSwitchingDevice", "Bedienteil", [box_solid(f, px + 0.16, posts_y[1] - 0.1, 1.2, px + 0.22, posts_y[1] + 0.1, 1.5)], keys=keys, predefined_type="MOMENTARYSWITCH")

    x0, w = 1.9, 0.85
    zb = zr + 0.25
    profile = [(x0, zb), (x0 + 4.3, zb), (x0 + 4.3, zb + 0.55), (x0 + 3.5, zb + 0.65), (x0 + 2.9, zb + 1.15), (x0 + 1.3, zb + 1.15), (x0 + 0.7, zb + 0.7), (x0, zb + 0.6)]
    s.add("IfcBuildingElementProxy", "Fahrzeug", [profile_y(f, profile, cy - w, cy + w)], object_type="Personenwagen")
    s.add("IfcBuildingElementProxy", "Raeder", [pipe_solid(f, (x, cy + d * (w - 0.22), zr + 0.32), (x, cy + d * (w + 0.02), zr + 0.32), 0.32, segments=40) for x in (x0 + 0.8, x0 + 3.4) for d in (-1, 1)], object_type="Rad")

    legs = [box_solid(f, x, y, 0.0, x + 0.05, y + 0.05, 0.85) for x in (6.05, 7.7) for y in (0.15, 0.7)]
    s.add("IfcFurniture", "Werkbank", [box_solid(f, 6.0, 0.1, 0.85, 7.8, 0.8, 0.9), *legs], predefined_type="TABLE")
    s.add("IfcBuildingElementProxy", "Reifen", [vertical_cylinder_solid(f, 0.6, 5.2, 0.22 * i, 0.33, 0.21, segments=40) for i in range(4)], object_type="Reifenstapel")
    return s


# ---------------------------------------------------------------------------
# Fahrtreppe / Fahrsteig
# ---------------------------------------------------------------------------


def _belt(s: Scene, keys, name: str, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float, flat: float = 1.2) -> None:
    """Escalator or walkway along X: truss, step band, glass balustrades and handrails."""
    f = s.ifc_file
    xa, xb = x0 + flat, x1 - flat

    def line(dz: float):
        return [(x0, z0 + dz), (xa, z0 + dz), (xb, z1 + dz), (x1, z1 + dz)]

    def band(lo: float, hi: float):
        bottom, top = line(lo), line(hi)
        return bottom + list(reversed(top))

    s.add("IfcTransportElement", name, [profile_y(f, band(-0.9 if z1 != z0 else -0.35, 0.0), y0, y1)], keys=keys, predefined_type="ESCALATOR" if z1 != z0 else "MOVINGWALKWAY")
    s.add("IfcBuildingElementProxy", f"{name}-Balustraden", [profile_y(f, band(0.1, 1.0), y, y + 0.03) for y in (y0 + 0.05, y1 - 0.08)], keys=keys, object_type="Balustrade", thin=True)
    s.add("IfcBuildingElementProxy", f"{name}-Handlaeufe", [part for y in (y0 + 0.065, y1 - 0.065) for part in polyline_solids(f, [(x, y, z) for x, z in line(1.03)], 0.045, segments=8)], keys=keys, object_type="Handlauf", thin=True)
    if z1 != z0:
        n = 14
        steps = []
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            xs, xe = xa + (xb - xa) * t0, xa + (xb - xa) * t1
            zs = max(z0 + (z1 - z0) * t0, z0 + (z1 - z0) * t1)
            steps.append(box_solid(f, xs, y0 + 0.12, zs - 0.06, xe, y1 - 0.12, zs))
        s.add("IfcBuildingElementProxy", f"{name}-Stufen", steps, keys=keys, object_type="Stufe", thin=True)
    else:
        s.add("IfcBuildingElementProxy", f"{name}-Palettenband", [box_solid(f, xa, y0 + 0.12, z0, xb, y1 - 0.12, z0 + 0.03)], keys=keys, object_type="Palettenband", thin=True)


def escalator() -> Scene:
    """Hall with an upper gallery; escalator from the floor to the gallery, people as context."""
    s = corner_room("Fahrtreppe", width=12.0, depth=7.0, height=7.0)
    f = s.ifc_file
    zg = 3.6
    x0, y0, y1, gap = 2.8, 1.6, 2.8, 0.02
    gallery = [(0.0, 0.0), (4.0, 0.0), (4.0, y0 - gap), (x0 - gap, y0 - gap), (x0 - gap, y1 + gap), (4.0, y1 + gap), (4.0, 7.0), (0.0, 7.0)]
    add_slab(f, name="Galerie", body_context=s.body_context, storey=s.storey, polyline=gallery, thickness=0.3, z_bottom=zg - 0.3, predefined_type="FLOOR")
    s.add("IfcRailing", "Galeriegelaender", [box_solid(f, 3.95, 3.2, zg, 4.0, 7.0, zg + 1.0)], predefined_type="GUARDRAIL", thin=True)
    s.add("IfcColumn", "Stuetzen", [box_solid(f, 3.6, y, 0.0, 3.9, y + 0.3, zg - 0.3) for y in (3.5, 6.6)], predefined_type="COLUMN")
    _belt(s, (ESCALATOR,), "Fahrtreppe", x0, 11.6, y0, y1, zg, 0.0)
    return s


def moving_walkway() -> Scene:
    """Long hall section with a moving walkway set flush into the floor slab beside a walking lane."""
    s = Scene.new("Fahrsteig", storey_name="UG")
    f = s.ifc_file
    width, depth, t, slab = 14.0, 6.0, 0.2, 0.25
    x0, x1, y0, y1, truss, pit_floor = 1.0, 13.0, 1.0, 2.4, 0.35, 0.25
    pit = rect_polyline(x0, y0, x1, y1)
    pit_outer = rect_polyline(x0 - t, y0 - t, x1 + t, y1 + t)
    s.add(
        "IfcSlab",
        "Bodenplatte",
        [
            extrude_with_voids(f, rect_polyline(-t, 0.0, width, depth), [pit], slab, z_bottom=-slab),
            extrude_with_voids(f, pit_outer, [pit], truss - slab, z_bottom=-truss),
            box_solid(f, x0 - t, y0 - t, -truss - pit_floor, x1 + t, y1 + t, -truss),
        ],
        predefined_type="FLOOR",
    )
    _belt(s, (MOVING_WALKWAY,), "Fahrsteig", x0, x1, y0, y1, 0.0, 0.0, flat=1.2)
    s.add("IfcBuildingElementProxy", "Gepaeckwagen", [box_solid(f, 6.0, 4.0, 0.15, 7.0, 4.6, 0.9)], object_type="Gepaeckwagen")
    return s


# ---------------------------------------------------------------------------
# Seilbahnen
# ---------------------------------------------------------------------------


def _station(s: Scene, name: str, x0: float, x1: float, y0: float, y1: float, z0: float, height: float, keys=()) -> None:
    f = s.ifc_file
    s.add("IfcColumn", f"{name}-Stuetzen", [box_solid(f, x, y, z0, x + 0.3, y + 0.3, z0 + height) for x in (x0, x1 - 0.3) for y in (y0, y1 - 0.3)], keys=keys, predefined_type="COLUMN")
    s.add("IfcRoof", f"{name}-Dach", [box_solid(f, x0 - 0.3, y0 - 0.3, z0 + height, x1 + 0.3, y1 + 0.3, z0 + height + 0.3)], keys=keys, predefined_type="FLAT_ROOF")
    s.add("IfcSlab", f"{name}-Boden", [box_solid(f, x0, y0, z0, x1, y1, z0 + 0.3)], keys=keys, predefined_type="FLOOR")


def cableway(kind: str = "aerial") -> Scene:
    """Ropeways: ``aerial`` (two cabins between valley and mountain station over a pylon), ``material``
    (track rope over an A-frame with a load carrier and a winch station) or ``target`` (shooting range:
    rope between two masts with a running target carriage and drive)."""
    s = Scene.new("Seilbahn", storey_name="Terrain")
    f = s.ifc_file
    if kind == "aerial":
        keys = (AERIAL_ROPEWAY,)
        length, rise, width = 24.0, 10.0, 9.0
        z = _slope(s, length, rise, width, top=5.0, bottom=5.0)
        cy = width / 2
        _station(s, "Bergstation", -4.6, 0.0, cy - 2.4, cy + 2.4, rise, 4.0, keys=keys)
        _station(s, "Talstation", length, length + 4.6, cy - 2.4, cy + 2.4, 0.0, 4.0, keys=keys)
        wheels = ((-2.3, rise + 3.0), (length + 2.3, 3.0))
        s.add("IfcBuildingElementProxy", "Seilscheiben", [vertical_cylinder_solid(f, x, cy, zw, 1.4, 0.2, segments=28) for x, zw in wheels], keys=keys, object_type="Umlenkscheibe")
        px = 11.0
        top = z(px) + 6.5
        s.add(
            "IfcBuildingElementProxy",
            "Stuetze",
            [box_solid(f, px - 0.8, cy - 0.8, z(px) - 0.2, px + 0.8, cy + 0.8, z(px) + 0.4), box_solid(f, px - 0.3, cy - 0.3, z(px) + 0.4, px + 0.3, cy + 0.3, top), box_solid(f, px - 0.3, cy - 2.0, top, px + 0.3, cy + 2.0, top + 0.4)],
            keys=keys,
            object_type="Seilbahnstuetze",
        )
        ropes = []
        for dy in (-1.4, 1.4):
            a = (-2.3, cy + dy, rise + 3.1)
            p = (px, cy + dy, top + 0.5)
            b = (length + 2.3, cy + dy, 3.1)
            ropes.extend(polyline_solids(f, _catenary(a, p, 0.6) + _catenary(p, b, 0.6)[1:], 0.06, segments=6))
        s.add("IfcBuildingElementProxy", "Seile", ropes, keys=keys, object_type="Tragseil", thin=True)
        cabins = []
        for cx, dy in ((5.0, 1.4), (17.5, -1.4)):
            zr = (rise + 3.1) + (top + 0.5 - rise - 3.1) * (cx + 2.3) / (px + 2.3) if cx < px else (top + 0.5) + (3.1 - top - 0.5) * (cx - px) / (length + 2.3 - px)
            zr -= 0.45
            cabins.append(box_solid(f, cx - 0.4, cy + dy - 0.2, zr - 0.2, cx + 0.4, cy + dy + 0.2, zr + 0.1))
            cabins.append(box_solid(f, cx - 0.05, cy + dy - 0.05, zr - 1.4, cx + 0.05, cy + dy + 0.05, zr - 0.2))
            cabins.append(box_solid(f, cx - 1.0, cy + dy - 0.9, zr - 3.4, cx + 1.0, cy + dy + 0.9, zr - 1.4))
        s.add("IfcTransportElement", "Kabinen", cabins, predefined_type="USERDEFINED", object_type="Seilbahnkabine")
    elif kind == "material":
        keys = (MATERIAL_ROPEWAY,)
        length, rise, width = 22.0, 9.0, 7.0
        z = _slope(s, length, rise, width, top=4.0, bottom=5.0)
        cy = width / 2
        s.add("IfcBuildingElementProxy", "Bergstation", [box_solid(f, -2.2, cy - 1.6, rise, -1.9, cy - 1.3, rise + 3.0), box_solid(f, -2.2, cy + 1.3, rise, -1.9, cy + 1.6, rise + 3.0), box_solid(f, -2.4, cy - 1.6, rise + 3.0, -1.7, cy + 1.6, rise + 3.3)], keys=keys, object_type="Endbock")
        s.add("IfcRoof", "Windenhaus-Dach", [box_solid(f, length + 0.5, cy - 2.0, 3.0, length + 4.5, cy + 2.0, 3.2)], keys=keys, predefined_type="FLAT_ROOF")
        s.add("IfcColumn", "Windenhaus-Stuetzen", [box_solid(f, x, y, 0.0, x + 0.2, y + 0.2, 3.0) for x in (length + 0.6, length + 4.2) for y in (cy - 1.9, cy + 1.7)], keys=keys, predefined_type="COLUMN")
        s.add("IfcBuildingElementProxy", "Seilwinde", [pipe_solid(f, (length + 2.2, cy - 0.8, 1.0), (length + 2.2, cy + 0.8, 1.0), 0.5, segments=20), box_solid(f, length + 2.9, cy - 0.6, 0.0, length + 3.9, cy + 0.6, 1.0), box_solid(f, length + 1.8, cy - 0.9, 0.0, length + 2.6, cy + 0.9, 0.5)], keys=keys, object_type="Seilwinde")
        px = 10.0
        top = z(px) + 5.0
        frame = [pipe_solid(f, (px, cy + d, z(px) - 0.1), (px, cy, top), 0.1, segments=8) for d in (-1.8, 1.8)]
        frame.append(pipe_solid(f, (px, cy - 0.9, (z(px) + top) / 2), (px, cy + 0.9, (z(px) + top) / 2), 0.07, segments=8))
        frame.append(box_solid(f, px - 0.3, cy - 0.3, top, px + 0.3, cy + 0.3, top + 0.2))
        s.add("IfcBuildingElementProxy", "Bockstuetze", frame, keys=keys, object_type="Bockstuetze")
        a = (-2.05, cy, rise + 3.0)
        p = (px, cy, top + 0.2)
        b = (length + 2.2, cy, 1.5)
        s.add("IfcBuildingElementProxy", "Tragseil", polyline_solids(f, _catenary(a, p, 0.5) + _catenary(p, b, 0.5)[1:], 0.05, segments=6), keys=keys, object_type="Tragseil", thin=True)
        cx = 15.5
        zr = (top + 0.2) + (1.5 - top - 0.2) * (cx - px) / (length + 2.2 - px) - 0.4
        s.add(
            "IfcTransportElement",
            "Lastwagen",
            [
                box_solid(f, cx - 0.4, cy - 0.12, zr - 0.15, cx + 0.4, cy + 0.12, zr + 0.15),
                box_solid(f, cx - 0.04, cy - 0.04, zr - 1.2, cx + 0.04, cy + 0.04, zr - 0.15),
                box_solid(f, cx - 0.8, cy - 0.6, zr - 1.3, cx + 0.8, cy + 0.6, zr - 1.2),
            ],
            predefined_type="USERDEFINED",
            object_type="Laufwerk mit Lastplattform",
        )
        s.add("IfcBuildingElementProxy", "Last", [box_solid(f, cx - 0.6, cy - 0.45, zr - 2.1, cx + 0.6, cy + 0.45, zr - 1.3)], object_type="Ladung")
    elif kind == "target":
        keys = (TARGET_ROPEWAY,)
        add_slab(f, name="Terrain", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(-2.0, 0.0, 26.0, 12.0), thickness=0.4, z_bottom=-0.4, predefined_type="BASESLAB")
        s.add("IfcGeographicElement", "Kugelfang", [profile_x(f, [(0.0, 0.0), (3.5, 0.0), (0.6, 3.5), (0.0, 3.5)], -2.0, 26.0)], predefined_type="TERRAIN")
        y = 5.0
        masts = []
        for x in (0.0, 24.0):
            masts.append(box_solid(f, x - 0.5, y - 0.5, -0.2, x + 0.5, y + 0.5, 0.3))
            masts.append(vertical_cylinder_solid(f, x, y, 0.3, 0.2, 3.6, segments=14))
        s.add("IfcMember", "Masten", masts, keys=keys, predefined_type="POST")
        s.add("IfcBuildingElementProxy", "Abspannungen", [pipe_solid(f, (x, y, 3.7), (x + dx, y, 0.0), 0.025, segments=6) for x, dx in ((0.0, -1.8), (24.0, 1.8))], keys=keys, object_type="Abspannseil", thin=True)
        s.add("IfcBuildingElementProxy", "Fahrseil", [pipe_solid(f, (0.0, y, 3.6), (24.0, y, 3.6), 0.04, segments=6)], keys=keys, object_type="Fahrseil", thin=True)
        s.add("IfcElectricMotor", "Antrieb", [box_solid(f, -1.6, y + 0.8, 0.0, -0.4, y + 1.8, 1.2), horizontal_cylinder(f, -1.4, -0.6, y + 1.3, 1.5, 0.3, segments=16)], keys=keys)
        s.add("IfcController", "Steuerung", [box_solid(f, 1.0, 9.6, 0.0, 1.6, 10.0, 1.4)], keys=keys)
        cx = 13.0
        s.add(
            "IfcTransportElement",
            "Zielwagen",
            [box_solid(f, cx - 0.5, y - 0.15, 3.35, cx + 0.5, y + 0.15, 3.8), box_solid(f, cx - 0.04, y - 0.04, 2.5, cx + 0.04, y + 0.04, 3.35)],
            predefined_type="USERDEFINED",
            object_type="Zielwagen",
        )
        s.add("IfcBuildingElementProxy", "Zielscheibe", [box_solid(f, cx - 0.45, y - 0.02, 0.8, cx + 0.45, y + 0.02, 2.5)], object_type="Figurenscheibe")
        s.add("IfcWall", "Deckungswall", [box_solid(f, -2.0, 7.5, 0.0, 26.0, 8.0, 0.8)], predefined_type="PARAPET")
    else:
        raise ValueError(f"unknown cableway {kind!r}")
    return s
