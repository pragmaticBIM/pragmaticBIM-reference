"""Wave 1 kitchen plan_symbol recipes."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.component_geometry import svg as svg_mod
from generators.component_geometry.bodies import local_box
from generators.component_geometry.types import GeometryContext, SvgPath


class CabinetRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=ctx.depth, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#f0e6d8"),
            svg_mod.line(w * 0.5, 0.0, w * 0.5, d, stroke="#1a1a1a", stroke_width=0.008),
        ]


class WallCabinetRecipe(CabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.rect(0.0, 0.0, w, d, fill="#f7f0e6", stroke="#1a1a1a", stroke_width=0.012, stroke_dasharray="0.04 0.02"),
        ]


class KitchenRunRecipe:
    """Linear kitchen: carcass + worktop thickness cue + sink bay."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        carcass = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=d, height=h * 0.95)
        worktop = local_box(ifc_file, x0=0.0, y0=0.0, z0=h * 0.95, x1=w, y1=d, height=h * 0.05)
        tall_w = min(0.6, w * 0.2)
        tall = local_box(ifc_file, x0=w - tall_w, y0=0.0, z0=0.0, x1=w, y1=d, height=min(2.2, h * 2.4))
        return [carcass, worktop, tall]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        tall_w = min(0.6, w * 0.2)
        sink_w = min(0.6, w * 0.25)
        sink_x = max(0.3, (w - tall_w - sink_w) * 0.4)
        return [
            svg_mod.footprint_rect(w, d, fill="#f0e6d8"),
            svg_mod.rect(w - tall_w, 0.0, tall_w, d, fill="#e0d0b8", stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.rect(
                sink_x,
                d * 0.15,
                sink_w,
                d * 0.55,
                fill="#ffffff",
                stroke="#1a1a1a",
                stroke_width=0.01,
            ),
            # Module ticks
            *[
                svg_mod.line(x, 0.0, x, d, stroke="#888888", stroke_width=0.006)
                for x in [i * 0.6 for i in range(1, int(w / 0.6))]
                if x < w - tall_w - 0.05
            ],
        ]


class KitchenLRecipe(KitchenRunRecipe):
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        # Main run along X; return leg along Y at the start (simplified L footprint still rectangular)
        main = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=min(0.6, d), height=h)
        leg_d = max(d - 0.6, d * 0.5)
        leg = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=min(0.6, w), y1=d, height=h)
        return [main, leg]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        run = min(0.6, d)
        leg = min(0.6, w)
        return [
            svg_mod.rect(0.0, 0.0, w, run, fill="#f0e6d8", stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.rect(0.0, 0.0, leg, d, fill="#f0e6d8", stroke="#1a1a1a", stroke_width=0.012),
        ]


class KitchenIslandRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        return [
            local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=d, height=h * 0.95),
            local_box(ifc_file, x0=0.0, y0=0.0, z0=h * 0.95, x1=w, y1=d, height=h * 0.05),
        ]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#f0e6d8"),
            svg_mod.rect(w * 0.15, d * 0.2, w * 0.7, d * 0.45, fill="#ffffff", stroke="#1a1a1a", stroke_width=0.01),
        ]


class CookingLineRecipe(CabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#ddd5cc"),
            svg_mod.circle(w * 0.3, d * 0.5, min(0.12, d * 0.25), fill="none", stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.circle(w * 0.7, d * 0.5, min(0.12, d * 0.25), fill="none", stroke="#1a1a1a", stroke_width=0.012),
        ]


class DishwashingLineRecipe(CabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e8eef5"),
            svg_mod.line(0.15 * w, 0.2 * d, 0.85 * w, 0.2 * d, stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.line(0.15 * w, 0.5 * d, 0.85 * w, 0.5 * d, stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.line(0.15 * w, 0.8 * d, 0.85 * w, 0.8 * d, stroke="#1a1a1a", stroke_width=0.01),
        ]


KITCHEN_RECIPES = {
    "tall_cabinet": CabinetRecipe(),
    "wall_cabinet": WallCabinetRecipe(),
    "kitchen_run": KitchenRunRecipe(),
    "kitchen_l": KitchenLRecipe(),
    "kitchen_island": KitchenIslandRecipe(),
    "cooking_line": CookingLineRecipe(),
    "dishwashing_line": DishwashingLineRecipe(),
}
