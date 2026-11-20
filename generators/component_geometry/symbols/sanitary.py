"""Wave 1 sanitary plan_symbol recipes."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.component_geometry import svg as svg_mod
from generators.component_geometry.bodies import local_box
from generators.component_geometry.types import GeometryContext, SvgPath


class WcRecipe:
    """Wall-hung WC: cistern block + oval bowl."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        cistern_d = min(0.14, d * 0.28)
        bowl_d = d - cistern_d
        cistern = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=cistern_d, height=h * 0.85)
        # Bowl as thinner extruded oval approximated by rectangle with inset
        inset = min(0.04, w * 0.1)
        bowl = local_box(
            ifc_file,
            x0=inset,
            y0=cistern_d,
            z0=0.0,
            x1=w - inset,
            y1=d,
            height=h * 0.55,
        )
        return [cistern, bowl]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        cistern_d = min(0.14, d * 0.28)
        return [
            svg_mod.rect(0.0, 0.0, w, cistern_d, fill="#e8e8e8", stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.ellipse(
                w / 2,
                cistern_d + (d - cistern_d) / 2,
                w * 0.38,
                (d - cistern_d) * 0.42,
                fill="#f5f5f5",
                stroke="#1a1a1a",
                stroke_width=0.012,
            ),
        ]


class WcAccessibleRecipe(WcRecipe):
    """Same as WC with a wider plan footprint marker."""

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        paths = super().plan(ctx)
        paths.append(
            svg_mod.rect(
                -0.02,
                -0.02,
                ctx.width + 0.04,
                ctx.depth + 0.04,
                fill="none",
                stroke="#1a1a1a",
                stroke_width=0.008,
                stroke_dasharray="0.04 0.02",
            )
        )
        return paths


class WashbasinRecipe:
    """Wall-hung washbasin: rim + bowl recess as stepped solids."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        rim = local_box(ifc_file, x0=0.0, y0=0.0, z0=h * 0.7, x1=w, y1=d, height=h * 0.3)
        # Pedestal / console under
        console = local_box(
            ifc_file,
            x0=w * 0.25,
            y0=0.0,
            z0=0.0,
            x1=w * 0.75,
            y1=d * 0.35,
            height=h * 0.7,
        )
        return [rim, console]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d),
            svg_mod.ellipse(
                w / 2,
                d * 0.55,
                w * 0.32,
                d * 0.28,
                fill="#ffffff",
                stroke="#1a1a1a",
                stroke_width=0.01,
            ),
        ]


class WashbasinDoubleRecipe(WashbasinRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d),
            svg_mod.ellipse(w * 0.28, d * 0.55, w * 0.16, d * 0.28, fill="#ffffff", stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.ellipse(w * 0.72, d * 0.55, w * 0.16, d * 0.28, fill="#ffffff", stroke="#1a1a1a", stroke_width=0.01),
        ]


class WashbasinRowRecipe(WashbasinRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        paths = [svg_mod.footprint_rect(w, d)]
        n = max(2, int(round(w / 0.6)))
        for i in range(n):
            cx = (i + 0.5) * w / n
            paths.append(
                svg_mod.ellipse(cx, d * 0.55, min(0.18, w / n * 0.35), d * 0.28, fill="#ffffff", stroke="#1a1a1a", stroke_width=0.01)
            )
        return paths


class WashbasinAccessibleRecipe(WashbasinRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        paths = super().plan(ctx)
        paths.append(
            svg_mod.rect(
                0.0,
                ctx.depth,
                ctx.width,
                0.7,
                fill="none",
                stroke="#888888",
                stroke_width=0.01,
                stroke_dasharray="0.05 0.03",
            )
        )
        return paths


class ShowerRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        # Thin tray
        tray_h = min(0.05, ctx.height)
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=ctx.depth, height=tray_h)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#eef6ff"),
            svg_mod.line(0.0, 0.0, w, d, stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.line(w, 0.0, 0.0, d, stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.circle(w * 0.5, d * 0.5, min(w, d) * 0.06, fill="none", stroke="#1a1a1a", stroke_width=0.01),
        ]


class BathtubRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        shell = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=d, height=h)
        return [shell]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        inset = 0.08
        return [
            svg_mod.footprint_rect(w, d),
            svg_mod.ellipse(
                w / 2,
                d / 2,
                w / 2 - inset,
                d / 2 - inset,
                fill="#ffffff",
                stroke="#1a1a1a",
                stroke_width=0.012,
            ),
        ]


class UrinalRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        return [
            local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=d * 0.4, height=h),
            local_box(ifc_file, x0=w * 0.15, y0=d * 0.4, z0=0.0, x1=w * 0.85, y1=d, height=h * 0.45),
        ]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.rect(0.0, 0.0, w, d * 0.35, fill="#e8e8e8", stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.ellipse(w / 2, d * 0.65, w * 0.35, d * 0.28, fill="#f5f5f5", stroke="#1a1a1a", stroke_width=0.012),
        ]


class SinkRecipe:
    """Kitchen / utility sink."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        top = local_box(ifc_file, x0=0.0, y0=0.0, z0=h * 0.85, x1=w, y1=d, height=h * 0.15)
        cabinet = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=d, height=h * 0.85)
        return [cabinet, top]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d),
            svg_mod.rect(
                w * 0.12,
                d * 0.15,
                w * 0.76,
                d * 0.55,
                fill="#ffffff",
                stroke="#1a1a1a",
                stroke_width=0.01,
            ),
        ]


SANITARY_RECIPES = {
    "wc": WcRecipe(),
    "wc_accessible": WcAccessibleRecipe(),
    "washbasin": WashbasinRecipe(),
    "washbasin_double": WashbasinDoubleRecipe(),
    "washbasin_row": WashbasinRowRecipe(),
    "washbasin_accessible": WashbasinAccessibleRecipe(),
    "shower": ShowerRecipe(),
    "bathtub": BathtubRecipe(),
    "urinal": UrinalRecipe(),
    "kitchen_sink": SinkRecipe(),
    "utility_sink": SinkRecipe(),
}
