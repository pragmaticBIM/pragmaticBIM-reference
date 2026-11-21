"""Annotated plan SVG of a room-type layout with its placement-rule status.

The base drawing (walls, openings, equipment symbols) comes from
:func:`generators.component_geometry.build_room_plan`. On top, every rule result
gets one annotation group carrying ``data-rule-id``:

- ``next_to`` / ``distance_to`` / ``facing``: dimension line with the measured value
- ``same_wall_as`` / ``not_on_wall_with`` / ``opposite``: highlighted wall segments
- ``elevation``: height label at the item
- ``not_in_clearance_of``: outline of the target's clearance zones

Colour follows the checker result: green when the rule is met, red when it is
violated. A met ``preferred`` rule is dashed, a met ``required`` rule solid.
Below the plan a legend lists every rule with id, relation, target and status.
"""

from __future__ import annotations

import math
import re
from typing import Any, Sequence
from xml.sax.saxutils import escape, quoteattr

from shapely.geometry import Point
from shapely.ops import nearest_points

from generators import room_rules as rr
from generators.component_geometry import build_room_plan

COLOR_OK = "#2e7d32"
COLOR_FAIL = "#c62828"
COLOR_CLEARANCE = "#ef6c00"
MARGIN = 0.5
"""Space around the room outline in metres (dimension labels sit there)."""
MIN_WIDTH = 8.5
"""Smallest drawing width in metres, so legend lines fit under narrow rooms."""
FONT = 0.11
ROW = 0.2
_DASH = "0.08 0.05"

_BASE_BODY = re.compile(r"<g transform=[^>]*>\n(.*)\n</g>\n</svg>", re.DOTALL)


def _color(result: rr.RuleResult) -> str:
    return COLOR_OK if result.ok else COLOR_FAIL


def _dash(result: rr.RuleResult) -> str:
    return f' stroke-dasharray="{_DASH}"' if result.ok and result.severity == "preferred" else ""


def _status(result: rr.RuleResult) -> str:
    return "ok" if result.ok else "fail"


def _fmt(measured: float | str | None, relation: str) -> str:
    if isinstance(measured, (int, float)):
        return f"{measured:.0f}°" if relation in ("facing", "opposite") else f"{measured:.2f} m"
    return "" if measured is None else str(measured)


def _text(x: float, y: float, content: str, color: str, *, anchor: str = "middle", size: float = FONT) -> str:
    """Text at room coordinates; undoes the Y flip of the plan group."""
    return (
        f'<text transform="translate({x:.4f} {y:.4f}) scale(1 -1)" text-anchor="{anchor}" '
        f'font-family="sans-serif" font-size="{size}" fill="{color}">{escape(content)}</text>'
    )


def _line(p: Sequence[float], q: Sequence[float], color: str, width: float, extra: str = "") -> str:
    return (
        f'<line x1="{p[0]:.4f}" y1="{p[1]:.4f}" x2="{q[0]:.4f}" y2="{q[1]:.4f}" '
        f'stroke="{color}" stroke-width="{width}"{extra} />'
    )


def _outline(polygon, color: str, width: float, extra: str = "") -> str:
    points = " ".join(f"{x:.4f},{y:.4f}" for x, y in list(polygon.exterior.coords)[:-1])
    return f'<polygon points="{points}" fill="none" stroke="{color}" stroke-width="{width}"{extra} />'


def _dimension(p: Sequence[float], q: Sequence[float], label: str, color: str, extra: str) -> list[str]:
    """Dimension line with end ticks and the value beside its middle."""
    mid = ((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)
    parts: list[str] = []
    length = math.dist(p, q)
    if length > 1e-6:
        parts.append(_line(p, q, color, 0.015, extra))
        nx, ny = -(q[1] - p[1]) / length, (q[0] - p[0]) / length
        for point in (p, q):
            tick = 0.05
            parts.append(_line((point[0] - nx * tick, point[1] - ny * tick), (point[0] + nx * tick, point[1] + ny * tick), color, 0.015))
    else:
        parts.append(f'<circle cx="{p[0]:.4f}" cy="{p[1]:.4f}" r="0.03" fill="{color}" />')
    if label:
        parts.append(_text(mid[0], mid[1] + 0.07, label, color))
    return parts


def _rule_index(config: dict[str, Any]) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {
        rule["id"]: (rule, entry)
        for _, entry in rr.configuration_entries(config)
        for rule in entry.get("placement_rules") or []
    }


def _gap(item: rr.Placed, target: rr.Target, room: rr.Room) -> float:
    return float(item.footprint.distance(rr._target_geometry(target, room)))


def _subject_and_target(
    result: rr.RuleResult,
    rule: dict[str, Any],
    layout: rr.Layout,
) -> tuple[rr.Placed | None, rr.Target | None]:
    """The item a result belongs to and the target the rule was measured against."""
    room = layout.room
    entry_items = [i for i in layout.items if i.entry_id == result.entry_id]
    if rule.get("scope") == "each_target":
        targets = rr.resolve_targets(rule.get("target"), layout, None)
        target = next((t for t in targets if rr._target_key(t) == result.element), None)
        if target is None or not entry_items:
            return None, target
        return min(entry_items, key=lambda i: _gap(i, target, room)), target
    subject = next((i for i in entry_items if i.key == result.element), None)
    if subject is None:
        return None, None
    targets = rr.resolve_targets(rule.get("target"), layout, subject)
    target = min(targets, key=lambda t: _gap(subject, t, room)) if targets else None
    return subject, target


def _annotation(
    result: rr.RuleResult,
    rule: dict[str, Any],
    layout: rr.Layout,
) -> list[str]:
    room = layout.room
    color = _color(result)
    dash = _dash(result)
    relation = rule["relation"]
    subject, target = _subject_and_target(result, rule, layout)
    if subject is None:
        return []
    parts = [_outline(subject.footprint, color, 0.025, dash)]
    label = _fmt(result.measured, relation)
    if relation == "elevation":
        x, y = subject.centre
        parts.append(_text(x, y, f"h {label}", color))
    elif relation == "next_to" and target is not None:
        a, b = nearest_points(subject.footprint, rr._target_geometry(target, room))
        parts.extend(_dimension((a.x, a.y), (b.x, b.y), label, color, dash))
    elif relation in ("distance_to", "facing") and target is not None:
        centre = subject.centre
        if relation == "distance_to":
            end = rr._target_centre(target, room, centre)
        else:
            point = nearest_points(rr._target_geometry(target, room), Point(centre))[0]
            end = (point.x, point.y)
        parts.extend(_dimension(centre, end, label, color, dash))
    elif relation in ("same_wall_as", "not_on_wall_with", "opposite") and target is not None:
        for edge in (rr.host_edge(subject, room), rr._target_wall(target, room)):
            if edge is not None:
                parts.append(_line(edge.start, edge.end, color, 0.07, f' stroke-opacity="0.55"{dash}'))
    elif relation == "not_in_clearance_of" and isinstance(target, rr.Placed):
        for zone in target.clearances:
            parts.append(_outline(zone, color, 0.025, dash))
    return parts


def _legend_text(result: rr.RuleResult, rule: dict[str, Any]) -> str:
    target = rr._target_text(rule.get("target")) if rule["relation"] != "elevation" else "elevation"
    state = "met" if result.ok else "violated"
    short = result.rule_id.rsplit("/", 1)[-1]
    measured = _fmt(result.measured, rule["relation"])
    text = f"{short} · {rule['relation']} · {target} · {result.severity} {state}"
    return f"{text} ({measured})" if measured else text


def build_annotated_plan_svg(
    layout: rr.Layout,
    config: dict[str, Any],
    rule_results: Sequence[rr.RuleResult],
    *,
    title: str | None = None,
) -> str:
    """Plan of ``layout`` with one annotation and one legend row per rule result.

    ``rule_results`` should come from :func:`generators.room_rules.evaluate_layout`
    with ``include_passed=True`` so met rules show too.
    """
    base = build_room_plan(layout, include_clearances=False)
    match = _BASE_BODY.search(base)
    if match is None:
        raise ValueError("unexpected base plan SVG")
    body = match.group(1)

    room = layout.room
    xs = [p[0] for p in room.outline]
    ys = [p[1] for p in room.outline]
    plan_w, plan_h = max(xs) - min(xs), max(ys) - min(ys)

    index = _rule_index(config)
    rows = [(result, index[result.rule_id][0]) for result in rule_results if result.rule_id in index]

    zones = [
        _outline(zone, COLOR_CLEARANCE, 0.01).replace('fill="none"', 'fill="url(#clearance-hatch)"')
        for item in layout.items
        for zone in item.clearances
    ]
    annotations = []
    for result, rule in rows:
        parts = _annotation(result, rule, layout)
        if parts:
            annotations.append(
                f'<g class="rule-annotation" data-rule-id={quoteattr(result.rule_id)} '
                f'data-relation="{rule["relation"]}" data-severity="{result.severity}" '
                f'data-status="{_status(result)}">\n' + "\n".join(parts) + "\n</g>"
            )

    width = max(plan_w + 2 * MARGIN, MIN_WIDTH)
    plan_bottom = plan_h + 2 * MARGIN
    legend_top = plan_bottom + 0.1
    height = legend_top + ROW * (len(rows) + 2)

    legend = [
        f'<text x="{MARGIN}" y="{legend_top + ROW * 0.8:.4f}" font-family="sans-serif" '
        f'font-size="{FONT * 1.2:.4f}" font-weight="bold" fill="#1a1a1a">'
        f"{escape(title or config['id'].rsplit('/', 1)[-1])}</text>"
    ]
    for number, (result, rule) in enumerate(rows, start=1):
        y = legend_top + ROW * (number + 1)
        color = _color(result)
        legend.append(
            f'<g class="legend-row" data-rule-id={quoteattr(result.rule_id)} data-status="{_status(result)}">'
            f'<line x1="{MARGIN}" y1="{y - FONT / 3:.4f}" x2="{MARGIN + 0.3}" y2="{y - FONT / 3:.4f}" '
            f'stroke="{color}" stroke-width="0.04"{_dash(result)} />'
            f'<text x="{MARGIN + 0.4}" y="{y:.4f}" font-family="sans-serif" font-size="{FONT}" fill="{color}">'
            f"{escape(_legend_text(result, rule))}</text></g>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 100:.1f}mm" height="{height * 100:.1f}mm" '
        f'viewBox="0 0 {width:.4f} {height:.4f}">\n'
        '<rect width="100%" height="100%" fill="#ffffff" />\n'
        '<defs><pattern id="clearance-hatch" width="0.1" height="0.1" patternUnits="userSpaceOnUse">'
        f'<path d="M 0 0.1 L 0.1 0" stroke="{COLOR_CLEARANCE}" stroke-width="0.01" /></pattern></defs>\n'
        f'<g transform="translate({MARGIN - min(xs):.4f} {MARGIN + max(ys):.4f}) scale(1 -1)">\n'
        f"{body}\n" + "\n".join(zones) + "\n" + "\n".join(annotations) + "\n</g>\n"
        '<g class="legend">\n' + "\n".join(legend) + "\n</g>\n</svg>\n"
    )
