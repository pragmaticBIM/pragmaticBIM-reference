"""Furniture, seating, beds, and workplace plan_symbol recipes."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.component_geometry import svg as svg_mod
from generators.component_geometry.bodies import local_box
from generators.component_geometry.types import GeometryContext, SvgPath


class BoxCabinetRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=ctx.depth, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        return [svg_mod.footprint_rect(ctx.width, ctx.depth, fill="#f0e6d8")]


class TableRecipe(BoxCabinetRecipe):
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        top_t = min(0.05, h * 0.1)
        top = local_box(ifc_file, x0=0.0, y0=0.0, z0=h - top_t, x1=w, y1=d, height=top_t)
        leg = min(0.06, w * 0.08)
        legs = [
            local_box(ifc_file, x0=x, y0=y, z0=0.0, x1=x + leg, y1=y + leg, height=h - top_t)
            for x, y in ((leg, leg), (w - 2 * leg, leg), (leg, d - 2 * leg), (w - 2 * leg, d - 2 * leg))
        ]
        return [top, *legs]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#f5efe6"),
            svg_mod.rect(0.08, 0.08, w - 0.16, d - 0.16, fill="none", stroke="#888888", stroke_width=0.008),
        ]


class DeskRecipe(TableRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#f5efe6"),
            svg_mod.rect(0.0, 0.0, w, min(0.08, d * 0.15), fill="#e0d5c5", stroke="#1a1a1a", stroke_width=0.008),
        ]


class SofaRecipe(BoxCabinetRecipe):
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        w, d, h = ctx.width, ctx.depth, ctx.height
        seat = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=d * 0.7, height=h * 0.55)
        back = local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=w, y1=d * 0.25, height=h)
        return [seat, back]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e8e0f0"),
            svg_mod.rect(0.0, 0.0, w, d * 0.25, fill="#d0c4e0", stroke="#1a1a1a", stroke_width=0.01),
        ]


class BedRecipe(BoxCabinetRecipe):
    def __init__(self, double: bool = False) -> None:
        self.double = double

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        paths = [
            svg_mod.footprint_rect(w, d, fill="#eef2f8"),
            svg_mod.rect(0.0, 0.0, w, min(0.15, d * 0.12), fill="#d0d8e8", stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.ellipse(w * 0.5, d * 0.22, w * 0.18, min(0.12, d * 0.1), fill="#ffffff", stroke="#1a1a1a", stroke_width=0.008),
        ]
        if self.double:
            paths.append(
                svg_mod.ellipse(w * 0.28, d * 0.22, w * 0.12, min(0.1, d * 0.08), fill="#ffffff", stroke="#1a1a1a", stroke_width=0.008)
            )
            paths.append(
                svg_mod.ellipse(w * 0.72, d * 0.22, w * 0.12, min(0.1, d * 0.08), fill="#ffffff", stroke="#1a1a1a", stroke_width=0.008)
            )
            paths = paths[:2] + paths[3:]
        return paths


class ShelfRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        paths = [svg_mod.footprint_rect(w, d, fill="#efe8dc")]
        for y in (0.25 * d, 0.5 * d, 0.75 * d):
            paths.append(svg_mod.line(0.05, y, w - 0.05, y, stroke="#888888", stroke_width=0.006))
        return paths


class ShelfDoubleRecipe(ShelfRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#efe8dc"),
            svg_mod.line(w * 0.5, 0.0, w * 0.5, d, stroke="#1a1a1a", stroke_width=0.01),
        ]


class WardrobeRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e8dcc8"),
            svg_mod.line(w * 0.5, 0.0, w * 0.5, d, stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.circle(w * 0.25, d * 0.5, 0.02, fill="none", stroke="#1a1a1a", stroke_width=0.008),
            svg_mod.circle(w * 0.75, d * 0.5, 0.02, fill="none", stroke="#1a1a1a", stroke_width=0.008),
        ]


class FilingCabinetRecipe(WardrobeRecipe):
    pass


class LockersRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        paths = [svg_mod.footprint_rect(w, d, fill="#dde5ee")]
        n = max(2, int(round(w / 0.35)))
        for i in range(1, n):
            x = i * w / n
            paths.append(svg_mod.line(x, 0.0, x, d, stroke="#1a1a1a", stroke_width=0.008))
        return paths


class PalletRackRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#d8d8d8"),
            svg_mod.rect(0.05, 0.05, w - 0.1, d - 0.1, fill="none", stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.line(0.05, d * 0.5, w - 0.05, d * 0.5, stroke="#1a1a1a", stroke_width=0.008),
        ]


class BenchRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        return [svg_mod.footprint_rect(ctx.width, ctx.depth, fill="#e8e0d0")]


class ChairRowRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        paths = [svg_mod.footprint_rect(w, d, fill="#f0f0f0")]
        n = max(2, int(round(w / 0.55)))
        for i in range(n):
            cx = (i + 0.5) * w / n
            paths.append(svg_mod.circle(cx, d * 0.45, min(0.18, w / n * 0.35), fill="#ffffff", stroke="#1a1a1a", stroke_width=0.01))
        return paths


class SeatRowDeskRecipe(ChairRowRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        paths = super().plan(ctx)
        paths.append(svg_mod.rect(0.0, d * 0.75, w, d * 0.25, fill="#e8e0d0", stroke="#1a1a1a", stroke_width=0.01))
        return paths


class CounterRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e6ddd0"),
            svg_mod.rect(0.0, 0.0, w, min(0.1, d * 0.2), fill="#d0c4b0", stroke="#1a1a1a", stroke_width=0.01),
        ]


class WallBoardRecipe(BoxCabinetRecipe):
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=min(0.05, ctx.depth), height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = ctx.width
        return [
            svg_mod.rect(0.0, 0.0, w, 0.04, fill="#2a4a6a", stroke="#1a1a1a", stroke_width=0.01),
        ]


class WorktopRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        return [svg_mod.footprint_rect(ctx.width, ctx.depth, fill="#ebe4da")]


class CareBedRecipe(BedRecipe):
    def __init__(self) -> None:
        super().__init__(double=False)

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        paths = super().plan(ctx)
        w, d = ctx.width, ctx.depth
        paths.append(svg_mod.rect(w - 0.12, d * 0.3, 0.1, d * 0.4, fill="#c0c8d8", stroke="#1a1a1a", stroke_width=0.008))
        return paths


class ExaminationCouchRecipe(BoxCabinetRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e8f0f0"),
            svg_mod.rect(0.0, 0.0, min(0.45, w * 0.35), d, fill="#d0e0e0", stroke="#1a1a1a", stroke_width=0.01),
        ]


FURNITURE_RECIPES = {
    "bed_double": BedRecipe(double=True),
    "bed_single": BedRecipe(double=False),
    "bistro_table": TableRecipe(),
    "dining_table": TableRecipe(),
    "desk": DeskRecipe(),
    "sofa": SofaRecipe(),
    "shelf": ShelfRecipe(),
    "shelf_double": ShelfDoubleRecipe(),
    "wardrobe": WardrobeRecipe(),
    "filing_cabinet": FilingCabinetRecipe(),
    "lockers": LockersRecipe(),
    "pallet_rack": PalletRackRecipe(),
    "bench": BenchRecipe(),
    "chair_row": ChairRowRecipe(),
    "seat_row_desk": SeatRowDeskRecipe(),
    "service_counter": CounterRecipe(),
    "reception_desk": CounterRecipe(),
    "checkout": CounterRecipe(),
    "worktop": WorktopRecipe(),
    "work_table": TableRecipe(),
    "meeting_table": TableRecipe(),
    "pupil_desk": DeskRecipe(),
    "workbench": TableRecipe(),
    "wall_board": WallBoardRecipe(),
    "care_bed": CareBedRecipe(),
    "examination_couch": ExaminationCouchRecipe(),
}
