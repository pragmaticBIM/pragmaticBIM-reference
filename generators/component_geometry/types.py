"""Shared types for component 2D/3D recipes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

import ifcopenshell

from generators import room_rules as rr


@dataclass(frozen=True)
class SvgPath:
    """One SVG path (or shape) in local or room coordinates, metres."""

    d: str
    kind: str = "path"
    """``path``, ``rect``, ``circle``, ``ellipse``, ``line``."""
    fill: str = "none"
    stroke: str = "#1a1a1a"
    stroke_width: float = 0.02
    stroke_dasharray: str | None = None
    attrs: dict[str, float | str] = field(default_factory=dict)


@dataclass
class GeometryContext:
    """Resolved placement + component data for one occurrence."""

    item: rr.Placed
    component: dict[str, Any]
    params: dict[str, float]
    language: str = "de"
    name: str = ""

    @property
    def width(self) -> float:
        return float(self.item.frame.width)

    @property
    def depth(self) -> float:
        return float(self.item.frame.depth)

    @property
    def height(self) -> float:
        return max(self.item.z_max - self.item.z_min, 0.01)

    @property
    def plan_symbol(self) -> str:
        return str(self.component.get("representation", {}).get("plan_symbol") or "")

    @property
    def body_kind(self) -> str:
        return str(self.component.get("representation", {}).get("body") or "box")


class Recipe(Protocol):
    """One plan_symbol recipe: 3D body solids in local axes + 2D plan paths."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        """Solids in the product local frame (origin back-left, X width, Y depth)."""

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        """Plan paths in local component axes (metres)."""
