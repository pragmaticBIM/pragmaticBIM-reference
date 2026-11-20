"""Generic body builders keyed by representation.body."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity

from generators import room_rules as rr
from generators.component_geometry.types import GeometryContext, SvgPath
from generators.component_geometry import svg as svg_mod
from generators.parts import (
    axis_placement_matrix,
    create_body_representation,
    create_extruded_area_solid,
)


def local_box(
    ifc_file: ifcopenshell.file,
    *,
    x0: float,
    y0: float,
    z0: float,
    x1: float,
    y1: float,
    height: float,
) -> ifcopenshell.entity_instance:
    """Extruded rectangle in the product local XY plane, bottom at z0."""
    return create_extruded_area_solid(
        ifc_file,
        [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
        height,
        origin=(0.0, 0.0, z0),
    )


def footprint_solid(ifc_file: ifcopenshell.file, ctx: GeometryContext) -> ifcopenshell.entity_instance:
    return local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=ctx.depth, height=ctx.height)


def create_product(
    ifc_file: ifcopenshell.file,
    body_context,
    ctx: GeometryContext,
    solids: Sequence[ifcopenshell.entity_instance],
) -> ifcopenshell.entity_instance:
    product = create_entity(
        ifc_file,
        ifc_class=rr.element_ifc_class(ctx.component),
        name=ctx.name or ctx.component.get("id", "component"),
        predefined_type=ctx.component.get("predefined_type"),
    )
    if ctx.component.get("object_type"):
        ot = ctx.component["object_type"]
        product.ObjectType = ot.get(ctx.language, ot.get("de", "")) if isinstance(ot, dict) else str(ot)
    edit_object_placement(
        ifc_file,
        product=product,
        matrix=axis_placement_matrix(
            (ctx.item.frame.origin[0], ctx.item.frame.origin[1], ctx.item.z_min),
            local_x=(ctx.item.frame.x_axis[0], ctx.item.frame.x_axis[1], 0.0),
            local_z=(0.0, 0.0, 1.0),
        ),
    )
    items = list(solids) if solids else [footprint_solid(ifc_file, ctx)]
    if len(items) == 1:
        shape = items[0]
    else:
        shape = items[0]
        for extra in items[1:]:
            shape = ifc_file.create_entity(
                "IfcBooleanResult", Operator="UNION", FirstOperand=shape, SecondOperand=extra
            )
    assign_representation(
        ifc_file, product=product, representation=create_body_representation(ifc_file, body_context, shape)
    )
    return product


def box_plan(ctx: GeometryContext) -> list[SvgPath]:
    return [svg_mod.footprint_rect(ctx.width, ctx.depth)]


def volume_plan(ctx: GeometryContext) -> list[SvgPath]:
    return [
        svg_mod.rect(
            0.0,
            0.0,
            ctx.width,
            ctx.depth,
            fill="#ffe8cc",
            stroke="#cc6600",
            stroke_width=0.02,
            stroke_dasharray="0.05 0.03",
        )
    ]


def opening_plan(ctx: GeometryContext, *, hinge_at_start: bool = True) -> list[SvgPath]:
    """Generic opening: wall cut as thin rectangle; doors refine via symbol."""
    leaf = min(0.05, ctx.depth)
    return [
        svg_mod.rect(0.0, 0.0, ctx.width, leaf, fill="#ffffff", stroke="#1a1a1a", stroke_width=0.012),
    ]
