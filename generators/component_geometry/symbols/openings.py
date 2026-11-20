"""Wave 1 door / window / passage plan_symbol recipes."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.component_geometry import svg as svg_mod
from generators.component_geometry.bodies import local_box
from generators.component_geometry.types import GeometryContext, SvgPath


def _hinge_at_start(ctx: GeometryContext) -> bool:
    return (ctx.item.hinge_end or "start") == "start"


class DoorSwingRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        # Thin door leaf extruded in the opening depth; leaf thickness ~45 mm
        leaf_t = min(0.045, ctx.depth)
        if _hinge_at_start(ctx):
            # Closed leaf along the opening (local X); sitting at back of frame
            return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=leaf_t, height=ctx.height)]
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=leaf_t, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = ctx.width
        hinge_start = _hinge_at_start(ctx)
        leaf = svg_mod.line(0.0, 0.0, w, 0.0, stroke="#1a1a1a", stroke_width=0.025)
        swing = svg_mod.door_swing_arc(w, hinge_at_start=hinge_start, sweep_into_room=True)
        return [leaf, swing]


class DoorDoubleRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        leaf_t = min(0.045, ctx.depth)
        mid = ctx.width / 2
        return [
            local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=mid, y1=leaf_t, height=ctx.height),
            local_box(ifc_file, x0=mid, y0=0.0, z0=0.0, x1=ctx.width, y1=leaf_t, height=ctx.height),
        ]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = ctx.width
        half = w / 2
        return [
            svg_mod.line(0.0, 0.0, w, 0.0, stroke="#1a1a1a", stroke_width=0.025),
            svg_mod.door_swing_arc(half, hinge_at_start=True, sweep_into_room=True),
            # Second leaf: hinge at end of opening — shift by drawing from mid
            svg_mod.path(
                f"M {half:.4f} 0 L {w:.4f} 0 A {half:.4f} {half:.4f} 0 0 0 {w:.4f} {half:.4f}",
                fill="none",
                stroke="#1a1a1a",
                stroke_width=0.015,
            ),
        ]


class DoorSlidingRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        leaf_t = min(0.045, ctx.depth)
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width * 0.55, y1=leaf_t, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = ctx.width
        return [
            svg_mod.line(0.0, 0.0, w, 0.0, stroke="#1a1a1a", stroke_width=0.02),
            svg_mod.rect(0.0, -0.03, w * 0.55, 0.06, fill="#dddddd", stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.path(
                f"M {w * 0.15:.4f} 0.08 L {w * 0.35:.4f} 0.08 L {w * 0.32:.4f} 0.12 M {w * 0.35:.4f} 0.08 L {w * 0.32:.4f} 0.04",
                fill="none",
                stroke="#1a1a1a",
                stroke_width=0.01,
            ),
        ]


class GateRecipe(DoorSwingRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = ctx.width
        return [
            svg_mod.line(0.0, 0.0, w, 0.0, stroke="#1a1a1a", stroke_width=0.03),
            svg_mod.door_swing_arc(w, hinge_at_start=_hinge_at_start(ctx), sweep_into_room=True),
            svg_mod.line(0.0, 0.05, w, 0.05, stroke="#1a1a1a", stroke_width=0.008, stroke_dasharray="0.06 0.03"),
        ]


class WindowRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        frame_t = min(0.06, ctx.depth)
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=frame_t, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = ctx.width
        return [
            svg_mod.line(0.0, 0.0, w, 0.0, stroke="#1a1a1a", stroke_width=0.02),
            svg_mod.line(0.0, 0.04, w, 0.04, stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.line(w * 0.5, 0.0, w * 0.5, 0.04, stroke="#1a1a1a", stroke_width=0.01),
        ]


class PassageRecipe:
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        # Minimal threshold strip
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=min(0.02, ctx.depth), height=0.02)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = ctx.width
        return [
            svg_mod.line(0.0, 0.0, w, 0.0, stroke="#1a1a1a", stroke_width=0.015, stroke_dasharray="0.05 0.03"),
        ]


OPENING_RECIPES = {
    "door_swing": DoorSwingRecipe(),
    "door_double": DoorDoubleRecipe(),
    "door_sliding": DoorSlidingRecipe(),
    "gate": GateRecipe(),
    "window": WindowRecipe(),
    "passage": PassageRecipe(),
}
