"""Small solid helpers on top of ``generators.mep_parts``."""

from __future__ import annotations

import math
from typing import Sequence

import ifcopenshell

from generators.parts import create_extruded_area_solid, create_faceted_brep, create_oriented_extruded_solid

Point3 = Sequence[float]


def prism(f: ifcopenshell.file, polygon: Sequence[Sequence[float]], z0: float, z1: float) -> ifcopenshell.entity_instance:
    """Plan ``polygon`` (x, y) extruded vertically from ``z0`` to ``z1``."""
    return create_extruded_area_solid(f, [tuple(p) for p in polygon], z1 - z0, origin=(0.0, 0.0, z0))


def profile_x(f: ifcopenshell.file, polygon: Sequence[Sequence[float]], x0: float, x1: float) -> ifcopenshell.entity_instance:
    """Section ``polygon`` (y, z) extruded along X from ``x0`` to ``x1``."""
    return create_oriented_extruded_solid(
        f, [tuple(p) for p in polygon], x1 - x0, origin=(x0, 0.0, 0.0), axis=(1.0, 0.0, 0.0), ref_direction=(0.0, 1.0, 0.0)
    )


def profile_y(f: ifcopenshell.file, polygon: Sequence[Sequence[float]], y0: float, y1: float) -> ifcopenshell.entity_instance:
    """Section ``polygon`` (x, z) extruded along Y from ``y0`` to ``y1``."""
    return create_oriented_extruded_solid(
        f, [(-x, z) for x, z in polygon], y1 - y0, origin=(0.0, y0, 0.0), axis=(0.0, 1.0, 0.0), ref_direction=(-1.0, 0.0, 0.0)
    )


def hexahedron(f: ifcopenshell.file, bottom: Sequence[Point3], top: Sequence[Point3]) -> ifcopenshell.entity_instance:
    """Closed six-sided solid; ``bottom`` and ``top`` are four corners, counter-clockwise seen from above."""
    vertices = [*bottom, *top]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return create_faceted_brep(f, vertices, faces)


def frustum(
    f: ifcopenshell.file,
    cx: float,
    cy: float,
    z_top: float,
    z_bottom: float,
    half_top: tuple[float, float],
    half_bottom: tuple[float, float],
) -> ifcopenshell.entity_instance:
    """Rectangular frustum (light cone, hopper) centred on ``(cx, cy)``."""
    tx, ty = half_top
    bx, by = half_bottom
    bottom = [(cx - bx, cy - by, z_bottom), (cx + bx, cy - by, z_bottom), (cx + bx, cy + by, z_bottom), (cx - bx, cy + by, z_bottom)]
    top = [(cx - tx, cy - ty, z_top), (cx + tx, cy - ty, z_top), (cx + tx, cy + ty, z_top), (cx - tx, cy + ty, z_top)]
    return hexahedron(f, bottom, top)


def octahedron(
    f: ifcopenshell.file,
    cx: float,
    cy: float,
    z_mid: float,
    radius: float,
    half_height: float,
) -> ifcopenshell.entity_instance:
    """Two square pyramids base to base (fire diamond); base corners on the X / Y axes at ``radius``."""
    vertices = [
        (cx, cy, z_mid - half_height),
        (cx + radius, cy, z_mid),
        (cx, cy + radius, z_mid),
        (cx - radius, cy, z_mid),
        (cx, cy - radius, z_mid),
        (cx, cy, z_mid + half_height),
    ]
    faces = []
    for i in range(4):
        j, k = 1 + i, 1 + (i + 1) % 4
        faces.append((j, k, 5))
        faces.append((k, j, 0))
    return create_faceted_brep(f, vertices, faces)


def pyramid(f: ifcopenshell.file, base: Sequence[Point3], apex: Point3) -> ifcopenshell.entity_instance:
    """Pyramid on a planar ``base`` polygon with its tip at ``apex``.

    ``base`` runs counter-clockwise seen from the apex (from above for an upright pyramid).
    """
    n = len(base)
    vertices = [*base, apex]
    faces = [tuple(reversed(range(n))), *((i, (i + 1) % n, n) for i in range(n))]
    return create_faceted_brep(f, vertices, faces)


def annular_sector(
    f: ifcopenshell.file,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    r_in: float,
    r_out: float,
    a0_deg: float,
    a1_deg: float,
    segments: int = 12,
) -> ifcopenshell.entity_instance:
    """Curved shell between ``r_in`` and ``r_out`` from ``a0_deg`` to ``a1_deg`` (counter-clockwise, 0° = +X)."""
    n1 = segments + 1
    angles = [math.radians(a0_deg + (a1_deg - a0_deg) * i / segments) for i in range(n1)]
    vertices = [
        (cx + r * math.cos(a), cy + r * math.sin(a), z)
        for z, r in ((z0, r_out), (z0, r_in), (z1, r_out), (z1, r_in))
        for a in angles
    ]
    ob, ib, ot, it = 0, n1, 2 * n1, 3 * n1
    faces = []
    for i in range(segments):
        j = i + 1
        faces.append((ob + i, ob + j, ot + j, ot + i))
        faces.append((ib + j, ib + i, it + i, it + j))
        faces.append((ob + i, ib + i, ib + j, ob + j))
        faces.append((ot + i, ot + j, it + j, it + i))
    faces.append((ob, ot, it, ib))
    faces.append((ob + segments, ib + segments, it + segments, ot + segments))
    return create_faceted_brep(f, vertices, faces)


def tilted_panel(
    f: ifcopenshell.file,
    x0: float,
    x1: float,
    y0: float,
    depth: float,
    z0: float,
    rise: float,
    thickness: float = 0.05,
) -> ifcopenshell.entity_instance:
    """Panel along X, rising by ``rise`` over ``depth`` towards −Y (faces +Y, south-up)."""
    y1 = y0 - depth
    bottom = [(x0, y1, z0 + rise), (x1, y1, z0 + rise), (x1, y0, z0), (x0, y0, z0)]
    top = [(x, y, z + thickness) for x, y, z in bottom]
    return hexahedron(f, bottom, top)
