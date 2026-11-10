"""Placement rules of room-type equipment and openings.

One module for the geometry and rule evaluation that both the room layout
generator (``generators/room_layout.py``) and the placement checker
(``checks/placement_rules.py``) use. Each side only translates its input into a
:class:`Layout` (a room outline plus placed items) and calls
:func:`evaluate_layout` / :func:`evaluate_rule`.

Conventions (plan in metres, heights above the room's finished floor):

- The room outline runs counter-clockwise; edge ``i`` goes from vertex ``i`` to
  ``i + 1`` and the room lies to its left.
- Every placed item has a :class:`Frame`: a rectangle with local X along its
  width and local Y along its depth, Y pointing to the item's front (into the
  room for wall-hosted components, into the declaring room for openings).
  This is the object placement written to and read from IFC.
- ``elevation`` is the underside above finished floor, as in component
  ``placement.elevation``.
- Opening jambs: ``hinge_end`` is the end of the opening along its host edge
  (``start`` or ``end``) where the leaf is hung or, for sliding doors, parks.
  The latch side is the other end.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import yaml
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points

REPO_ROOT = Path(__file__).resolve().parents[1]

TOLERANCE = 0.01
"""Length tolerance for range comparisons, in metres."""
WALL_TOLERANCE = 0.05
"""An item within this distance of an edge stands on that wall."""
WALL_BAND = 0.5
"""Openings and items within this distance of an edge line belong to that wall (wall thickness)."""
AREA_TOLERANCE = 1e-4
"""Overlap below this area (m²) counts as touching, not intruding."""
FACING_MAX_ANGLE = 45.0
"""``facing``: largest angle between the item's front and the direction to the target, in degrees."""
OPPOSITE_MIN_ANGLE = 135.0
"""``opposite``: smallest angle between the two walls' inward normals, in degrees."""

POSITIVE_RELATIONS = frozenset({"next_to", "opposite", "same_wall_as", "distance_to", "facing"})
NEGATIVE_RELATIONS = frozenset({"not_on_wall_with", "not_in_clearance_of"})
RELATIONS = POSITIVE_RELATIONS | NEGATIVE_RELATIONS | {"elevation"}

Vec = tuple[float, float]


# ── Reference data ───────────────────────────────────────────────────────────


@lru_cache(maxsize=None)
def _load_dir(folder: str) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for path in sorted((REPO_ROOT / folder).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        items[data["id"]] = data
    return items


def room_types() -> dict[str, dict[str, Any]]:
    return _load_dir("room_types")


def component(component_id: str) -> dict[str, Any]:
    return _load_dir("components")[component_id]


def element_ifc_class(component_data: dict[str, Any]) -> str:
    return str(_load_dir("elements")[component_data["element"]]["entity_ifc4"])


def room_type(ref: str) -> dict[str, Any]:
    """Room type by id (``pragmaticbim:room-type/buero``) or slug (``buero``)."""
    key = ref if ref.startswith("pragmaticbim:") else f"pragmaticbim:room-type/{ref}"
    return room_types()[key]


def configuration(room_type_data: dict[str, Any], configuration_id: str | None = None) -> dict[str, Any]:
    """The named configuration, or the first active one."""
    configurations = room_type_data.get("configurations") or []
    if configuration_id is not None:
        return next(c for c in configurations if c["id"] == configuration_id)
    return next(c for c in configurations if c.get("status", "active") == "active")


def configuration_entries(config: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Active equipment and opening entries as ``(kind, entry)``."""
    for kind, key in (("equipment", "equipment"), ("opening", "openings")):
        for entry in config.get(key) or []:
            if entry.get("status", "active") == "active":
                yield kind, entry


def component_parameters(
    component_data: dict[str, Any], overrides: dict[str, Any] | None = None
) -> dict[str, float]:
    """Parameter values for one placed instance: component defaults narrowed by room-type ``params``."""
    values = {key: float(spec["default"]) for key, spec in component_data["parameters"].items()}
    for key, spec in (overrides or {}).items():
        if key not in values:
            continue
        if isinstance(spec, dict):
            value = float(spec.get("default", values[key]))
            if "min" in spec:
                value = max(value, float(spec["min"]))
            if "max" in spec:
                value = min(value, float(spec["max"]))
        else:
            value = float(spec)
        values[key] = value
    return values


def resolve_length(value: Any, params: dict[str, float]) -> float:
    """A component length: a number or the name of one of its parameters."""
    return float(params[value]) if isinstance(value, str) else float(value)


def condition_met(
    condition: dict[str, Any] | None,
    selection: dict[str, Iterable[str]] | None,
) -> bool:
    """``when``/``unless`` semantics: every key matches; within a key, any entry is enough."""
    if not condition:
        return True
    chosen = {key: set(values) for key, values in (selection or {}).items()}
    return all(set(entries) & chosen.get(key, set()) for key, entries in condition.items())


# ── Plan geometry ────────────────────────────────────────────────────────────


def _unit(v: Sequence[float]) -> Vec:
    length = math.hypot(v[0], v[1])
    if length < 1e-12:
        raise ValueError("zero-length direction")
    return (v[0] / length, v[1] / length)


def _rot90(v: Vec) -> Vec:
    return (-v[1], v[0])


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _angle(a: Vec, b: Vec) -> float:
    a, b = _unit(a), _unit(b)
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(a, b)))))


@dataclass(frozen=True)
class Frame:
    """Rectangle of a placed item: origin at the back corner, X along width, Y towards the front."""

    origin: Vec
    x_axis: Vec
    width: float
    depth: float

    @property
    def y_axis(self) -> Vec:
        return _rot90(self.x_axis)

    def point(self, u: float, v: float) -> Vec:
        x, y = self.x_axis, self.y_axis
        return (self.origin[0] + u * x[0] + v * y[0], self.origin[1] + u * x[1] + v * y[1])

    def rect(self, u0: float, u1: float, v0: float, v1: float) -> Polygon:
        return Polygon([self.point(u0, v0), self.point(u1, v0), self.point(u1, v1), self.point(u0, v1)])

    @property
    def footprint(self) -> Polygon:
        return self.rect(0.0, self.width, 0.0, self.depth)

    @property
    def centre(self) -> Vec:
        return self.point(self.width / 2.0, self.depth / 2.0)

    @classmethod
    def facing(cls, centre: Vec, front: Vec, width: float, depth: float) -> "Frame":
        """Frame of a ``width`` × ``depth`` item centred on ``centre`` whose front points along ``front``."""
        f = _unit(front)
        x_axis = (f[1], -f[0])
        origin = (
            centre[0] - x_axis[0] * width / 2.0 - f[0] * depth / 2.0,
            centre[1] - x_axis[1] * width / 2.0 - f[1] * depth / 2.0,
        )
        return cls(origin, x_axis, width, depth)

    @classmethod
    def from_points(cls, points: Iterable[Sequence[float]], x_axis: Sequence[float]) -> "Frame":
        """Smallest frame with the given X direction that contains ``points`` (plan of an IFC body)."""
        x = _unit(x_axis)
        y = _rot90(x)
        us, vs = [], []
        for p in points:
            us.append(p[0] * x[0] + p[1] * x[1])
            vs.append(p[0] * y[0] + p[1] * y[1])
        u0, v0 = min(us), min(vs)
        origin = (u0 * x[0] + v0 * y[0], u0 * x[1] + v0 * y[1])
        return cls(origin, x, max(us) - u0, max(vs) - v0)


def clearance_polygons(
    component_data: dict[str, Any],
    params: dict[str, float],
    frame: Frame,
    selection: dict[str, Iterable[str]] | None = None,
) -> list[Polygon]:
    """Clearance rectangles of a component placed in ``frame``.

    Left and right are as seen standing in front of the component: left is +X.
    ``offset`` moves front/back/swing clearances to the right (−X) and left/right
    clearances towards the front (+Y).
    """
    width, depth = frame.width, frame.depth
    polygons: list[Polygon] = []
    for clearance in component_data.get("clearances") or []:
        if not condition_met(clearance.get("when"), selection):
            continue
        cw = resolve_length(clearance["width"], params)
        cd = resolve_length(clearance["depth"], params)
        offset = float(clearance.get("offset", 0.0))
        side = clearance["side"]
        if side in ("front", "swing", "back"):
            cu = width / 2.0 - offset
            v0, v1 = (depth, depth + cd) if side != "back" else (-cd, 0.0)
            polygons.append(frame.rect(cu - cw / 2.0, cu + cw / 2.0, v0, v1))
        else:
            cv = depth / 2.0 + offset
            u0, u1 = (width, width + cd) if side == "left" else (-cd, 0.0)
            polygons.append(frame.rect(u0, u1, cv - cw / 2.0, cv + cw / 2.0))
    return polygons


@dataclass(frozen=True)
class Edge:
    index: int
    start: Vec
    end: Vec
    kind: str

    @property
    def length(self) -> float:
        return math.dist(self.start, self.end)

    @property
    def direction(self) -> Vec:
        return _unit((self.end[0] - self.start[0], self.end[1] - self.start[1]))

    @property
    def normal(self) -> Vec:
        """Inward normal (the room lies to the left of a counter-clockwise edge)."""
        return _rot90(self.direction)

    @property
    def segment(self) -> LineString:
        return LineString([self.start, self.end])

    def point_at(self, t: float, s: float = 0.0) -> Vec:
        d, n = self.direction, self.normal
        return (self.start[0] + t * d[0] + s * n[0], self.start[1] + t * d[1] + s * n[1])

    def project(self, p: Sequence[float]) -> tuple[float, float]:
        """``(t, s)``: distance along the edge from its start, signed distance into the room."""
        rel = (p[0] - self.start[0], p[1] - self.start[1])
        return _dot(rel, self.direction), _dot(rel, self.normal)

    def interval(self, polygon: Polygon) -> tuple[float, float]:
        ts = [self.project(p)[0] for p in polygon.exterior.coords]
        return min(ts), max(ts)

    def describe(self) -> str:
        return f"edge {self.index} ({self.kind})"


class Room:
    """Room outline with one edge kind per edge (``interior``, ``exterior``, ``party_wall``, ``shaft``)."""

    def __init__(self, outline: Sequence[Sequence[float]], edge_kinds: Sequence[str] | None = None) -> None:
        points = [(float(p[0]), float(p[1])) for p in outline]
        if len(points) > 1 and points[0] == points[-1]:
            points.pop()
        if len(points) < 3:
            raise ValueError("room outline needs at least three points")
        kinds = list(edge_kinds) if edge_kinds is not None else ["interior"] * len(points)
        if len(kinds) != len(points):
            raise ValueError("edge_kinds needs one entry per outline edge")
        polygon = Polygon(points)
        if not polygon.is_valid or polygon.area <= 0:
            raise ValueError("room outline must be a simple polygon")
        self.reversed = not polygon.exterior.is_ccw
        """True when the outline was given clockwise: edge ``i`` became edge ``n - 1 - i``."""
        if self.reversed:
            # Reversing the vertex order reverses the edges; keep each kind on its edge.
            points = [points[0]] + points[:0:-1]
            kinds = kinds[::-1]
            polygon = Polygon(points)
        self.outline: list[Vec] = points
        self.edge_kinds: list[str] = kinds
        self.polygon = polygon
        self.edges = [
            Edge(i, points[i], points[(i + 1) % len(points)], kinds[i]) for i in range(len(points))
        ]

    @property
    def area(self) -> float:
        return float(self.polygon.area)


@dataclass
class Placed:
    """An equipment item or opening placed in (or in the wall of) a room."""

    key: str
    kind: str  # "equipment" | "opening"
    function: str | None
    frame: Frame
    z_min: float
    z_max: float
    entry_id: str | None = None
    component_id: str | None = None
    clearances: list[Polygon] = field(default_factory=list)
    edge_index: int | None = None
    hinge_end: str | None = None

    @property
    def footprint(self) -> Polygon:
        return self.frame.footprint

    @property
    def centre(self) -> Vec:
        return self.frame.centre


@dataclass
class Layout:
    room: Room
    items: list[Placed]
    key: str | None = None

    def matching(self, kind: str, function: str) -> list[Placed]:
        return [item for item in self.items if item.kind == kind and item.function == function]


def host_edge(item: Placed, room: Room) -> Edge | None:
    """The wall an item stands on: its opening edge, else the closest edge it touches, back wall first."""
    if item.edge_index is not None:
        return room.edges[item.edge_index]
    footprint = item.footprint
    touching = [e for e in room.edges if e.segment.distance(footprint) <= WALL_TOLERANCE]
    if not touching:
        return None
    front = item.frame.y_axis
    return max(touching, key=lambda e: (round(_dot(e.normal, front), 6), -e.segment.distance(footprint)))


def opening_edge(frame: Frame, room: Room) -> Edge | None:
    """Edge whose wall holds an opening body: parallel, within :data:`WALL_BAND`, overlapping along it."""
    footprint = frame.footprint
    best: tuple[float, Edge] | None = None
    for edge in room.edges:
        if abs(_dot(edge.direction, frame.x_axis)) < 0.9:
            continue
        distance = edge.segment.distance(footprint)
        t0, t1 = edge.interval(footprint)
        if distance > WALL_BAND or t1 < 0 or t0 > edge.length:
            continue
        if best is None or distance < best[0]:
            best = (distance, edge)
    return best[1] if best else None


_LEFT_HUNG = ("SINGLE_SWING_LEFT", "SLIDING_TO_LEFT", "FOLDING_TO_LEFT", "DOUBLE_DOOR_SINGLE_SWING_OPPOSITE_LEFT")
_RIGHT_HUNG = ("SINGLE_SWING_RIGHT", "SLIDING_TO_RIGHT", "FOLDING_TO_RIGHT", "DOUBLE_DOOR_SINGLE_SWING_OPPOSITE_RIGHT")


def hinge_end(frame: Frame, operation_type: str | None, edge: Edge) -> str | None:
    """Edge end of the hinge (or parking) jamb from an IFC door ``OperationType``.

    IFC: ``*_LEFT`` hangs the leaf on the left as seen looking along the door's +Y,
    i.e. at local X = 0 of its frame; ``*_RIGHT`` at X = width.
    """
    if operation_type in _LEFT_HUNG:
        u = 0.0
    elif operation_type in _RIGHT_HUNG:
        u = frame.width
    else:
        return None
    t0, t1 = edge.interval(frame.footprint)
    t = edge.project(frame.point(u, frame.depth / 2.0))[0]
    return "start" if abs(t - t0) <= abs(t - t1) else "end"


def operation_type(frame: Frame, end: str, edge: Edge, *, sliding: bool = False) -> str:
    """Inverse of :func:`hinge_end`: the IFC ``OperationType`` that hangs the leaf at ``end``."""
    left = "SLIDING_TO_LEFT" if sliding else "SINGLE_SWING_LEFT"
    right = "SLIDING_TO_RIGHT" if sliding else "SINGLE_SWING_RIGHT"
    return left if hinge_end(frame, left, edge) == end else right


# ── Rule evaluation ──────────────────────────────────────────────────────────

Target = Placed | Edge


@dataclass(frozen=True)
class Outcome:
    """One relation measured for one item: ``badness`` is 0 when met and grows with the miss."""

    ok: bool
    measured: float | str | None
    badness: float
    note: str = ""


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    entry_id: str
    element: str | None
    severity: str
    relation: str
    ok: bool
    measured: float | str | None
    expected: str
    message: str
    space: str | None = None


def _range_badness(value: float, bounds: dict[str, float] | None) -> float:
    bounds = bounds or {}
    lo, hi = bounds.get("min"), bounds.get("max")
    if lo is not None and value < lo - TOLERANCE:
        return lo - value
    if hi is not None and value > hi + TOLERANCE:
        return value - hi
    return 0.0


def _range_text(bounds: dict[str, float] | None) -> str:
    bounds = bounds or {}
    lo, hi = bounds.get("min"), bounds.get("max")
    if lo is not None and hi is not None:
        return f"{lo:.2f} m" if lo == hi else f"{lo:.2f}–{hi:.2f} m"
    if hi is not None:
        return f"≤ {hi:.2f} m"
    return f"≥ {lo:.2f} m"


def _target_text(target: dict[str, str] | None) -> str:
    if not target:
        return "finished floor"
    (key, value), = target.items()
    return {"equipment_function": "equipment", "opening_function": "opening", "edge_kind": "edge"}[key] + f" {value}"


def expected_text(body: dict[str, Any]) -> str:
    relation = body["relation"]
    target = _target_text(body.get("target"))
    if relation == "elevation":
        return f"elevation {_range_text(body.get('value'))}"
    if relation in ("next_to", "distance_to"):
        side = f" ({body['side']})" if body.get("side") else ""
        return f"{relation} {target}{side} {_range_text(body.get('distance'))}"
    return f"{relation} {target}"


def resolve_targets(target: dict[str, str] | None, layout: Layout, subject: Placed | None) -> list[Target]:
    if not target:
        return []
    (key, value), = target.items()
    if key == "edge_kind":
        return [edge for edge in layout.room.edges if edge.kind == value]
    kind = "equipment" if key == "equipment_function" else "opening"
    return [item for item in layout.matching(kind, value) if item is not subject]


def _target_key(target: Target) -> str:
    return target.key if isinstance(target, Placed) else target.describe()


def _target_geometry(target: Target, room: Room):
    """What distances are measured to: an opening's span on the wall line, an item's footprint, an edge."""
    if isinstance(target, Edge):
        return target.segment
    if target.kind == "opening" and target.edge_index is not None:
        edge = room.edges[target.edge_index]
        t0, t1 = edge.interval(target.footprint)
        return LineString([edge.point_at(t0), edge.point_at(t1)])
    return target.footprint


def _target_wall(target: Target, room: Room) -> Edge | None:
    return target if isinstance(target, Edge) else host_edge(target, room)


def _target_centre(target: Target, room: Room, towards: Vec) -> Vec:
    geometry = _target_geometry(target, room)
    if isinstance(target, Edge):
        point = nearest_points(geometry, Point(towards))[0]
        return (point.x, point.y)
    centroid = geometry.centroid
    return (centroid.x, centroid.y)


def _jamb_outcome(subject: Placed, target: Placed, body: dict[str, Any], room: Room) -> Outcome:
    edge = room.edges[target.edge_index] if target.edge_index is not None else None
    if edge is None:
        return Outcome(False, None, math.inf, "opening is not in a wall of the room")
    t0, t1 = edge.interval(target.footprint)
    hinge = target.hinge_end
    if body["side"] == "latch_side":
        ends = ["end" if hinge == "start" else "start"] if hinge else ["start", "end"]
    else:
        ends = [hinge] if hinge else ["start", "end"]
    a, b = edge.interval(subject.footprint)
    s = edge.project(subject.centre)[1]
    outcomes = []
    for end in ends:
        t_jamb = t1 if end == "end" else t0
        jamb = Point(edge.point_at(t_jamb))
        straight = float(subject.footprint.distance(jamb))
        if abs(s) > WALL_BAND:
            outcomes.append(Outcome(False, round(straight, 3), straight + 1.0, "not on the wall of the opening"))
            continue
        beyond = a >= t_jamb - TOLERANCE if end == "end" else b <= t_jamb + TOLERANCE
        if not beyond:
            outcomes.append(Outcome(False, round(straight, 3), straight + 1.0, f"not on the {body['side']}"))
            continue
        gap = max(0.0, a - t_jamb) if end == "end" else max(0.0, t_jamb - b)
        badness = _range_badness(gap, body.get("distance"))
        outcomes.append(Outcome(badness == 0.0, round(gap, 3), badness))
    return min(outcomes, key=lambda o: o.badness)


def _pair_outcome(subject: Placed, target: Target, body: dict[str, Any], room: Room) -> Outcome:
    relation = body["relation"]
    if relation == "next_to":
        if body.get("side") and isinstance(target, Placed):
            return _jamb_outcome(subject, target, body, room)
        distance = float(subject.footprint.distance(_target_geometry(target, room)))
        badness = _range_badness(distance, body.get("distance"))
        return Outcome(badness == 0.0, round(distance, 3), badness)
    if relation == "distance_to":
        centre = subject.centre
        if isinstance(target, Edge):
            distance = float(Point(centre).distance(target.segment))
        else:
            distance = math.dist(centre, _target_centre(target, room, centre))
        badness = _range_badness(distance, body.get("distance"))
        return Outcome(badness == 0.0, round(distance, 3), badness)
    if relation in ("same_wall_as", "not_on_wall_with", "opposite"):
        own = host_edge(subject, room)
        other = _target_wall(target, room)
        measured = own.describe() if own else "no wall"
        if relation == "opposite":
            if own is None or other is None:
                return Outcome(False, None, 180.0, "not on a wall")
            angle = _angle(own.normal, other.normal)
            return Outcome(angle >= OPPOSITE_MIN_ANGLE, round(angle, 1), max(0.0, OPPOSITE_MIN_ANGLE - angle))
        same = own is not None and other is not None and own.index == other.index
        ok = same if relation == "same_wall_as" else not same
        return Outcome(ok, measured, 0.0 if ok else 1.0)
    if relation == "facing":
        centre = subject.centre
        point = nearest_points(_target_geometry(target, room), Point(centre))[0]
        direction = (point.x - centre[0], point.y - centre[1])
        if math.hypot(*direction) < 1e-9:
            return Outcome(True, 0.0, 0.0)
        angle = _angle(subject.frame.y_axis, direction)
        return Outcome(angle <= FACING_MAX_ANGLE, round(angle, 1), max(0.0, angle - FACING_MAX_ANGLE))
    if relation == "not_in_clearance_of":
        zones = target.clearances if isinstance(target, Placed) else []
        area = sum(float(subject.footprint.intersection(zone).area) for zone in zones)
        return Outcome(area <= AREA_TOLERANCE, round(area, 4), area if area > AREA_TOLERANCE else 0.0)
    raise ValueError(f"unknown relation {relation!r}")


def evaluate_body(
    body: dict[str, Any],
    subject: Placed,
    layout: Layout,
    targets: Sequence[Target] | None = None,
) -> Outcome:
    """Evaluate one rule body (a rule without its variants) for one item.

    Positive relations hold when they hold for at least one target, negative
    ones when they hold for every target. ``targets`` overrides the targets
    named in the body (used for ``each_target`` rules).
    """
    relation = body["relation"]
    if relation not in RELATIONS:
        raise ValueError(f"unknown relation {relation!r}")
    room = layout.room
    if relation == "elevation":
        badness = _range_badness(subject.z_min, body.get("value"))
        outcome = Outcome(badness == 0.0, round(subject.z_min, 3), badness)
    else:
        candidates = list(targets) if targets is not None else resolve_targets(body.get("target"), layout, subject)
        if not candidates:
            ok = relation in NEGATIVE_RELATIONS
            outcome = Outcome(ok, None, 0.0 if ok else math.inf, "" if ok else "no target in the room")
        else:
            outcomes = [_pair_outcome(subject, target, body, room) for target in candidates]
            if relation in NEGATIVE_RELATIONS:
                worst = max(outcomes, key=lambda o: o.badness)
                if relation == "not_in_clearance_of":
                    area = round(sum(float(o.measured or 0.0) for o in outcomes), 4)
                    worst = Outcome(all(o.ok for o in outcomes), area, sum(o.badness for o in outcomes))
                outcome = worst
            else:
                outcome = min(outcomes, key=lambda o: o.badness)
    if subject.kind == "equipment":
        inside = room.polygon.buffer(WALL_TOLERANCE).contains(Point(subject.centre))
        wanted = body.get("room_side", "inside")
        if inside != (wanted == "inside"):
            note = "outside the room" if wanted == "inside" else "inside the room"
            return Outcome(False, outcome.measured, outcome.badness + 1.0, note)
    return outcome


def evaluate_rule(
    rule: dict[str, Any],
    subject: Placed,
    layout: Layout,
    targets: Sequence[Target] | None = None,
) -> Outcome:
    """A rule holds when its own body or any of its ``variants`` holds."""
    outcome = evaluate_body(rule, subject, layout, targets)
    if outcome.ok:
        return outcome
    for index, variant in enumerate(rule.get("variants") or [], start=1):
        alternative = evaluate_body(variant, subject, layout, targets)
        if alternative.ok:
            return Outcome(True, alternative.measured, 0.0, f"variant {index}")
    return outcome


def _message(rule: dict[str, Any], outcome: Outcome, element: str | None) -> str:
    state = "meets" if outcome.ok else "violates"
    text = f"{element or 'room'} {state} {expected_text(rule)}"
    if outcome.measured is not None:
        text += f" (measured {outcome.measured})"
    if outcome.note:
        text += f": {outcome.note}"
    return text


def evaluate_layout(
    layout: Layout,
    config: dict[str, Any],
    *,
    include_passed: bool = False,
) -> list[RuleResult]:
    """Evaluate every placement rule of a room-type configuration against a layout."""
    results: list[RuleResult] = []
    for kind, entry in configuration_entries(config):
        rules = entry.get("placement_rules") or []
        if not rules:
            continue
        subjects = [item for item in layout.items if item.kind == kind and item.entry_id == entry["id"]]
        for rule in rules:
            pairs: list[tuple[str | None, Outcome]] = []
            if rule.get("scope") == "each_target":
                for target in resolve_targets(rule.get("target"), layout, None):
                    candidates = [evaluate_rule(rule, s, layout, [target]) for s in subjects if s is not target]
                    if not candidates:
                        candidates = [Outcome(False, None, math.inf, "no item to serve it")]
                    best = min(candidates, key=lambda o: o.badness)
                    pairs.append((_target_key(target), best))
            else:
                pairs = [(s.key, evaluate_rule(rule, s, layout)) for s in subjects]
            for element, outcome in pairs:
                if outcome.ok and not include_passed:
                    continue
                results.append(
                    RuleResult(
                        rule_id=rule["id"],
                        entry_id=entry["id"],
                        element=element,
                        severity=rule["severity"],
                        relation=rule["relation"],
                        ok=outcome.ok,
                        measured=outcome.measured,
                        expected=expected_text(rule),
                        message=_message(rule, outcome, element),
                        space=layout.key,
                    )
                )
    return results
