"""Small solid helpers on top of ``generators.mep_parts``."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.parts import create_faceted_brep

Point3 = Sequence[float]


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
