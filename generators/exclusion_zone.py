"""IfcBuildingElementProxy Sperrzone on the shared structural vignette."""

from __future__ import annotations

from typing import Any

import ifcopenshell

from generators.structural_core import (
    add_solid_product,
    apply_attributes,
    box_solid,
    build_structural_core,
)

# Metres — punching zone around the column head, band in the upper wall
DEFAULT_SLAB_ZONE_MARGIN = 0.60
DEFAULT_WALL_ZONE_WIDTH = 1.20
DEFAULT_STOREY_HEIGHT = 2.60
DEFAULT_UPPER_WALL_HEIGHT = 2.00
# Oversize past host faces so translucent faces do not flicker against them
_OVERSIZE = 0.01


def generate_exclusion_zone(
    params: dict[str, Any],
) -> tuple[ifcopenshell.file, list[ifcopenshell.entity_instance]]:
    """Base slab, column, floor slab and an upper wall; accent two Sperrzonen.

    Zone A sits in the floor slab around the column head (punching zone).
    Zone B is a full-height band in the wall standing on the floor slab,
    at the wall section nearest the column.

    ``params`` keys:
    - ``attrs``: YAML-resolved attributes (Name, PredefinedType, ObjectType)
    - ``slab_zone_margin`` / ``wall_zone_width`` / ``wall_zone_x0`` (m)
    - ``storey_height`` / ``upper_wall_height`` (m)

    Returns ``(ifc_file, [slab_zone, wall_zone])``.
    """
    core = build_structural_core(
        {
            "project_name": params.get("project_name") or "Sperrzone",
            "wall": "floor",
            "floor_slab": "full",
            "wall_height": float(params.get("storey_height", DEFAULT_STOREY_HEIGHT)),
            "upper_wall_height": float(
                params.get("upper_wall_height", DEFAULT_UPPER_WALL_HEIGHT)
            ),
        }
    )
    ifc_file = core.ifc_file
    attrs = dict(params.get("attrs") or {})
    base_name = str(attrs.get("Name") or "SZ-01")

    margin = float(params.get("slab_zone_margin", DEFAULT_SLAB_ZONE_MARGIN))
    cx, cy = core.column_center
    half = core.column_size / 2 + margin
    slab_zone = add_solid_product(
        core,
        ifc_class="IfcBuildingElementProxy",
        name=base_name,
        solids=box_solid(
            ifc_file,
            cx - half,
            cy - half,
            cx + half,
            cy + half,
            core.floor_bottom - _OVERSIZE,
            core.floor_top + _OVERSIZE,
        ),
        predefined_type="USERDEFINED",
    )

    band_w = float(params.get("wall_zone_width", DEFAULT_WALL_ZONE_WIDTH))
    band_x0 = float(params.get("wall_zone_x0", cx - band_w / 2))
    wall_zone = add_solid_product(
        core,
        ifc_class="IfcBuildingElementProxy",
        name=_next_name(base_name),
        solids=box_solid(
            ifc_file,
            band_x0,
            -_OVERSIZE,
            band_x0 + band_w,
            core.wall_thickness + _OVERSIZE,
            core.wall_bottom,
            core.wall_top + _OVERSIZE,
        ),
        predefined_type="USERDEFINED",
    )

    apply_attributes(ifc_file, slab_zone, attrs, Description="Durchstanzbereich")
    apply_attributes(
        ifc_file, wall_zone, attrs, Name=wall_zone.Name, Description="Wandscheibe"
    )
    return ifc_file, [slab_zone, wall_zone]


def _next_name(name: str) -> str:
    """``SZ-01`` → ``SZ-02``; otherwise append ``-02``."""
    prefix, sep, number = name.rpartition("-")
    if sep and number.isdigit():
        return f"{prefix}-{int(number) + 1:0{len(number)}d}"
    return f"{name}-02"
