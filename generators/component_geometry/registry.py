"""Dispatch plan_symbol → recipe; unknown symbols fall back to box / footprint."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.component_geometry import svg as svg_mod
from generators.component_geometry.bodies import footprint_solid
from generators.component_geometry.symbols import RECIPES
from generators.component_geometry.types import GeometryContext, Recipe, SvgPath


class BoxFallback:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [footprint_solid(ifc_file, ctx)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        fill = "#ffe8cc" if ctx.body_kind == "volume" else "#f5f5f5"
        dash = "0.05 0.03" if ctx.body_kind == "volume" else None
        return [
            svg_mod.rect(
                0.0,
                0.0,
                ctx.width,
                ctx.depth,
                fill=fill,
                stroke="#1a1a1a",
                stroke_width=0.015,
                stroke_dasharray=dash,
            )
        ]


_FALLBACK = BoxFallback()


def get_recipe(plan_symbol: str) -> Recipe:
    return RECIPES.get(plan_symbol, _FALLBACK)


def known_symbols() -> frozenset[str]:
    return frozenset(RECIPES)
