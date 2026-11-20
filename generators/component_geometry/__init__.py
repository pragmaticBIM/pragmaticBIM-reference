"""Parametric 2D plan symbols and 3D IFC bodies for components.

``representation.plan_symbol`` selects a recipe; ``picture_link`` /
``attachment_link`` on the component YAML are optional catalog previews at
default parameters and are not used at place time.
"""

from __future__ import annotations

from typing import Any, Sequence

import ifcopenshell

from generators import room_rules as rr
from generators.component_geometry import svg as svg_mod
from generators.component_geometry.bodies import create_product
from generators.component_geometry.registry import get_recipe, known_symbols
from generators.component_geometry.types import GeometryContext, SvgPath

WAVE1_CATEGORIES = frozenset({"sanitary", "kitchen", "door", "window", "passage"})
"""Historical first wave; every active component now has a recipe."""

__all__ = [
    "WAVE1_CATEGORIES",
    "GeometryContext",
    "SvgPath",
    "build_body",
    "build_plan",
    "build_room_plan",
    "component_plan_svg",
    "geometry_context",
    "known_symbols",
]


def geometry_context(
    item: rr.Placed,
    component: dict[str, Any] | None = None,
    *,
    language: str = "de",
    name: str = "",
    params: dict[str, float] | None = None,
) -> GeometryContext:
    component = component or rr.component(item.component_id)
    resolved = params if params is not None else rr.component_parameters(component)
    return GeometryContext(
        item=item,
        component=component,
        params=resolved,
        language=language,
        name=name,
    )


def build_body(
    ifc_file: ifcopenshell.file,
    body_context,
    item: rr.Placed,
    component: dict[str, Any],
    *,
    language: str = "de",
    name: str = "",
) -> ifcopenshell.entity_instance:
    """Create an IFC product with a recipe-driven Body representation."""
    ctx = geometry_context(item, component, language=language, name=name)
    recipe = get_recipe(ctx.plan_symbol)
    solids = list(recipe.body_solids(ifc_file, ctx))
    return create_product(ifc_file, body_context, ctx, solids)


def build_plan(
    item: rr.Placed,
    component: dict[str, Any] | None = None,
    *,
    include_clearances: bool = False,
    room_coords: bool = False,
) -> list[SvgPath]:
    """Plan paths for one placed item (local axes, or room XY when ``room_coords``)."""
    component = component or rr.component(item.component_id)
    ctx = geometry_context(item, component)
    recipe = get_recipe(ctx.plan_symbol)
    paths = list(recipe.plan(ctx))
    if include_clearances:
        for poly in item.clearances:
            coords = list(poly.exterior.coords)[:-1]
            if not room_coords:
                # Clearance polygons are already in room coords — skip local overlay
                continue
            d = "M " + " L ".join(f"{x:.4f} {y:.4f}" for x, y in coords) + " Z"
            paths.append(
                SvgPath(
                    d=d,
                    kind="path",
                    fill="none",
                    stroke="#888888",
                    stroke_width=0.01,
                    stroke_dasharray="0.05 0.03",
                )
            )
    if room_coords:
        return svg_mod.transform_local_to_room(paths, item.frame)
    return paths


def build_room_plan(
    layout: rr.Layout,
    *,
    include_clearances: bool = False,
    wall_thickness: float = 0.12,
) -> str:
    """Full SVG of the room outline, walls, and placed component symbols."""
    room = layout.room
    paths: list[SvgPath] = []
    outline = list(room.outline)
    if outline and outline[0] != outline[-1]:
        outline = outline + [outline[0]]
    d = "M " + " L ".join(f"{float(x):.4f} {float(y):.4f}" for x, y in outline)
    paths.append(SvgPath(d=d, kind="path", fill="#fafafa", stroke="#333333", stroke_width=0.03))

    for edge in room.edges:
        # Wall band drawn outside the room (negative local Y of edge)
        pts = [
            edge.point_at(0.0, 0.0),
            edge.point_at(edge.length, 0.0),
            edge.point_at(edge.length, -wall_thickness),
            edge.point_at(0.0, -wall_thickness),
        ]
        wd = "M " + " L ".join(f"{x:.4f} {y:.4f}" for x, y in pts) + " Z"
        paths.append(SvgPath(d=wd, kind="path", fill="#e0e0e0", stroke="#666666", stroke_width=0.01))

    for item in layout.items:
        if not item.component_id:
            continue
        component = rr.component(item.component_id)
        item_paths = build_plan(item, component, include_clearances=False, room_coords=True)
        paths.extend(item_paths)
        if include_clearances:
            for poly in item.clearances:
                coords = list(poly.exterior.coords)[:-1]
                cd = "M " + " L ".join(f"{x:.4f} {y:.4f}" for x, y in coords) + " Z"
                paths.append(
                    SvgPath(
                        d=cd,
                        kind="path",
                        fill="none",
                        stroke="#888888",
                        stroke_width=0.01,
                        stroke_dasharray="0.05 0.03",
                    )
                )

    xs = [float(p[0]) for p in room.outline]
    ys = [float(p[1]) for p in room.outline]
    return svg_mod.document(paths, min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))


def component_plan_svg(
    component: dict[str, Any],
    *,
    params: dict[str, float] | None = None,
) -> str:
    """Standalone SVG preview of a component at default (or overridden) parameters."""
    resolved = params or rr.component_parameters(component)
    width = float(resolved.get("width", resolved.get("clear_width", 1.0)))
    if "depth" in resolved:
        depth = float(resolved["depth"])
    elif component.get("representation", {}).get("body") == "opening":
        depth = 0.1
    else:
        depth = 0.6
    height = float(resolved.get("height", resolved.get("clear_height", 1.0)))
    frame = rr.Frame((0.0, 0.0), (1.0, 0.0), width, depth)
    item = rr.Placed(
        key="preview",
        kind="opening" if component.get("representation", {}).get("body") == "opening" else "equipment",
        function=None,
        frame=frame,
        z_min=0.0,
        z_max=height,
        component_id=component["id"],
        hinge_end="start",
    )
    paths = build_plan(item, component)
    return svg_mod.document(paths, min_x=-0.05, min_y=-0.05, max_x=width + 0.05, max_y=depth + max(width, 0.2) + 0.05)
