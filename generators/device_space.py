"""IfcBuildingElementProxy Geräteplatz — device spaces in an operating theatre."""

from __future__ import annotations

from typing import Any

import ifcopenshell

from generators.base import create_project_shell, get_body_context
from generators.parts import add_extruded_product, rect_polyline
from generators.slab import add_slab
from generators.wall import add_wall

# Metres — operating theatre of about 45 m² (RT-HE-04). Back and left wall only,
# so the camera looks into the room over the open front and right side.
DEFAULT_INTERIOR_WIDTH = 6.80
DEFAULT_INTERIOR_DEPTH = 6.60
DEFAULT_WALL_THICKNESS = 0.15
DEFAULT_WALL_HEIGHT = 3.00
DEFAULT_SLAB_THICKNESS = 0.25

# Operating table space: table 0.60 × 2.10 plus team zone around it.
DEFAULT_TABLE_SPACE_WIDTH = 2.40
DEFAULT_TABLE_SPACE_DEPTH = 3.60
DEFAULT_TABLE_SPACE_HEIGHT = 1.10
# Anaesthesia workstation at the head end of the table.
DEFAULT_DEVICE_SIZE = 0.90
DEFAULT_DEVICE_HEIGHT = 1.60
DEFAULT_DEVICE_GAP = 0.30

# Context: wall-mounted cabinets on the back wall, a pendant column footprint.
DEFAULT_CABINET_DEPTH = 0.45
DEFAULT_CABINET_HEIGHT = 2.10


def generate_device_space(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list[ifcopenshell.entity_instance]]:
    """Build an operating theatre with two device spaces.

    The Operationstisch space sits in the room centre; the Medizingerät space
    (anaesthesia workstation) stands at its head end. Cabinets on the back wall
    stay white context. Returns ``(ifc_file, device_spaces)``.
    """
    params = dict(params or {})
    inner_w = float(params.get("interior_width", DEFAULT_INTERIOR_WIDTH))
    inner_d = float(params.get("interior_depth", DEFAULT_INTERIOR_DEPTH))
    wall_t = float(params.get("wall_thickness", DEFAULT_WALL_THICKNESS))
    wall_h = float(params.get("wall_height", DEFAULT_WALL_HEIGHT))
    slab_t = float(params.get("slab_thickness", DEFAULT_SLAB_THICKNESS))
    table_w = float(params.get("table_space_width", DEFAULT_TABLE_SPACE_WIDTH))
    table_d = float(params.get("table_space_depth", DEFAULT_TABLE_SPACE_DEPTH))
    table_h = float(params.get("table_space_height", DEFAULT_TABLE_SPACE_HEIGHT))
    device_s = float(params.get("device_size", DEFAULT_DEVICE_SIZE))
    device_h = float(params.get("device_height", DEFAULT_DEVICE_HEIGHT))

    if min(inner_w, inner_d, wall_t, wall_h, slab_t, table_w, table_d, table_h, device_s, device_h) <= 0:
        raise ValueError("all device-space dimensions must be positive")

    object_type = params.get("object_type") or params.get("ObjectType") or "Geräteplatz"
    predefined_type = params.get("predefined_type") or "USERDEFINED"

    x0, y0 = wall_t, wall_t
    x1, y1 = wall_t + inner_w, wall_t + inner_d

    # Table space centred; device at the head end (towards the back wall).
    cx = x0 + inner_w * 0.5
    cy = y0 + inner_d * 0.5 + 0.90
    table = (cx - table_w * 0.5, cy - table_d * 0.5, cx + table_w * 0.5, cy + table_d * 0.5)
    device_y1 = table[1] - DEFAULT_DEVICE_GAP
    device = (cx - device_s * 0.5, device_y1 - device_s, cx + device_s * 0.5, device_y1)
    cabinet_y1 = y0 + DEFAULT_CABINET_DEPTH
    if device[1] < cabinet_y1 + 0.6 or table[3] > y1 or table[0] < x0 or table[2] > x1:
        raise ValueError("device spaces do not fit inside the operating theatre")

    specs = params.get("device_spaces") or [
        ("Operationstisch", *table, table_h),
        ("Medizingerät", *device, device_h),
    ]

    ifc_file, _project, _site, _building, storey, body_context = create_project_shell(
        params.get("project_name") or "Geräteplatz",
        storey_name="EG",
    )
    body_context = get_body_context(ifc_file) or body_context

    add_slab(
        ifc_file,
        name="Bodenplatte",
        body_context=body_context,
        storey=storey,
        polyline=rect_polyline(0.0, 0.0, x1, y1),
        thickness=slab_t,
        z_bottom=-slab_t,
        predefined_type="FLOOR",
    )
    add_wall(
        ifc_file,
        name="Rueckwand",
        body_context=body_context,
        storey=storey,
        origin=(0.0, 0.0, 0.0),
        length=x1,
        height=wall_h,
        thickness=wall_t,
        direction_xy=(1.0, 0.0),
        predefined_type="PARTITIONING",
    )
    add_wall(
        ifc_file,
        name="Seitenwand-Links",
        body_context=body_context,
        storey=storey,
        origin=(0.0, y1, 0.0),
        length=inner_d,
        height=wall_h,
        thickness=wall_t,
        direction_xy=(0.0, -1.0),
        predefined_type="PARTITIONING",
    )
    # Built-in cabinets along the back wall, interrupted where the device stands.
    for name, cab_x0, cab_x1 in (
        ("Einbauschrank-Links", x0 + 0.40, cx - 1.40),
        ("Einbauschrank-Rechts", cx + 1.40, x1 - 0.40),
    ):
        add_extruded_product(
            ifc_file,
            ifc_class="IfcFurniture",
            name=name,
            body_context=body_context,
            storey=storey,
            polyline=rect_polyline(cab_x0, y0, cab_x1, cabinet_y1),
            thickness=DEFAULT_CABINET_HEIGHT,
            z_bottom=0.0,
            predefined_type="USERDEFINED",
        )

    spaces: list[ifcopenshell.entity_instance] = []
    for name, sx0, sy0, sx1, sy1, height in specs:
        if min(sx1 - sx0, sy1 - sy0, height) <= 0:
            raise ValueError(f"device space {name!r} has non-positive extent")
        proxy = add_extruded_product(
            ifc_file,
            ifc_class="IfcBuildingElementProxy",
            name=str(name),
            body_context=body_context,
            storey=storey,
            polyline=rect_polyline(sx0, sy0, sx1, sy1),
            thickness=height,
            z_bottom=0.0,
            predefined_type=predefined_type,
        )
        proxy.ObjectType = object_type
        spaces.append(proxy)

    return ifc_file, spaces
