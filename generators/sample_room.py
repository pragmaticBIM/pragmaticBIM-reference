"""Sample room for a room-type configuration.

Room-type pictures need a concrete room. This module derives a rectangular
outline from the configuration's ``NetPlannedArea`` (ratio 4:3, or
:data:`DEFAULT_AREA` when the configuration names none) and places the
configuration's openings on its edges:

| Edge | Position | Opening function |
| --- | --- | --- |
| 0 | south | ``access`` |
| 1 | east | ``outdoor_access`` |
| 2 | north | ``daylight`` |
| 3 | west | ``connection`` |

A single door sits near a corner, several openings of one edge are spread
evenly. The room grows when the openings of an edge do not fit its length, so
the area can end up above ``NetPlannedArea``. Areas above :data:`MAX_AREA` are
capped, so the placement search stays fast and the plan readable on A4. A
configuration may override all of this with ``sample_layout`` (``outline`` and
``openings`` as accepted by
:func:`generators.room_layout.generate_room_layout`) for corridors and halls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from generators import room_rules as rr
from generators.room_layout import OpeningSpec

DEFAULT_AREA = 12.0
"""Floor area in m² when the configuration has no numeric ``NetPlannedArea``."""
ASPECT = 4.0 / 3.0
"""Length to depth ratio of the sample room."""
MAX_AREA = 40.0
"""Largest sample room in m²; halls are drawn at this size so the picture stays readable."""
MIN_SIDE = 1.5
"""Shortest room side in metres."""
OPENING_MARGIN = 0.2
"""Clear wall length kept beside each opening, in metres."""
CORNER_OFFSET = 0.25
"""Distance between a single door's jamb and the corner, in metres."""

_EDGE_BY_FUNCTION = {"access": 0, "outdoor_access": 1, "daylight": 2, "connection": 3}


@dataclass
class SampleRoom:
    outline: list[tuple[float, float]]
    openings: list[OpeningSpec]

    @property
    def area(self) -> float:
        x0, y0 = self.outline[0]
        x1, y1 = self.outline[2]
        return abs(x1 - x0) * abs(y1 - y0)


def net_planned_area(config: dict[str, Any]) -> float:
    """``NetPlannedArea`` preset in m², or :data:`DEFAULT_AREA`."""
    for preset in config.get("attribute_presets") or []:
        if preset.get("name") == "NetPlannedArea":
            value = preset.get("value")
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                return float(value)
    return DEFAULT_AREA


def _opening_count(entry: dict[str, Any]) -> int:
    quantity = entry["quantity"]
    if isinstance(quantity, int):
        return quantity
    return int(quantity.get("default", quantity["min"]))


def _opening_width(entry: dict[str, Any]) -> float:
    component = rr.component(entry["components"][0])
    params = rr.component_parameters(component, entry.get("params"))
    return float(params.get("clear_width", params.get("width", 1.0)))


def _offsets(widths: list[float], length: float, *, centred: bool) -> list[float]:
    """Centre of each opening along an edge of ``length``."""
    if len(widths) == 1 and centred:
        return [length / 2.0]
    if len(widths) == 1:
        near_corner = widths[0] / 2.0 + CORNER_OFFSET
        return [min(near_corner, length / 2.0)]
    return [length * (i + 1) / (len(widths) + 1) for i in range(len(widths))]


def sample_room(config: dict[str, Any]) -> SampleRoom:
    """Outline and openings of the sample room of one configuration."""
    override = config.get("sample_layout")
    if override:
        outline = [(float(x), float(y)) for x, y in override["outline"]]
        return SampleRoom(outline, [OpeningSpec(**spec) for spec in override.get("openings") or []])

    entries = [
        entry
        for kind, entry in rr.configuration_entries(config)
        if kind == "opening" and entry["function"] in _EDGE_BY_FUNCTION
    ]
    per_edge: dict[int, list[tuple[dict[str, Any], float]]] = {}
    for entry in entries:
        width = _opening_width(entry)
        for _ in range(_opening_count(entry)):
            per_edge.setdefault(_EDGE_BY_FUNCTION[entry["function"]], []).append((entry, width))
    needed = {
        edge: sum(width + 2 * OPENING_MARGIN for _, width in items) for edge, items in per_edge.items()
    }

    area = min(net_planned_area(config), MAX_AREA)
    length = max(round(math.sqrt(area * ASPECT), 2), MIN_SIDE, needed.get(0, 0.0), needed.get(2, 0.0))
    depth = max(round(area / length, 2), MIN_SIDE, needed.get(1, 0.0), needed.get(3, 0.0))
    outline = [(0.0, 0.0), (length, 0.0), (length, depth), (0.0, depth)]
    edge_lengths = {0: length, 1: depth, 2: length, 3: depth}

    openings: list[OpeningSpec] = []
    for edge in sorted(per_edge):
        items = per_edge[edge]
        offsets = _offsets([w for _, w in items], edge_lengths[edge], centred=items[0][0]["function"] == "daylight")
        for (entry, _), offset in zip(items, offsets):
            openings.append(
                OpeningSpec(function=entry["function"], edge=edge, offset=round(offset, 3), entry=entry["id"])
            )
    return SampleRoom(outline, openings)
