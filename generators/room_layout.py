"""Lay out one room from its room-type configuration.

Takes a room outline, its openings and a room type, places every equipment item
the configuration orders and writes the room as IFC with the components'
box representations. ``required`` placement rules are hard constraints,
``preferred`` rules are scored; the rule geometry is shared with the checker
in :mod:`generators.room_rules`.

Nothing is dropped silently: an item without a position that meets its
required rules is listed in :attr:`RoomLayoutResult.unplaced`, and every rule
the finished layout does not meet is listed in :attr:`RoomLayoutResult.issues`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import ifcopenshell
from ifcopenshell.api.feature import add_feature, add_filling
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity
from ifcopenshell.api.spatial import assign_container
from shapely.geometry import LineString

from generators import room_rules as rr
from generators.base import assign_pset, create_project_shell, get_body_context
from generators.parts import (
    add_extruded_product,
    axis_placement_matrix,
    create_body_representation,
    create_extruded_area_solid,
    translation_matrix,
)
from generators.space import _create_space_entity

WALL_STEP = 0.05
"""Spacing of candidate positions along a wall, in metres."""
GRID_STEP = 0.2
"""Spacing of candidate positions for free-standing items, in metres."""
WALL_THICKNESS = {"exterior": 0.30, "party_wall": 0.25, "shaft": 0.15, "interior": 0.12}
DEFAULT_HEIGHT = 1.0
"""Body height for components without a ``height`` parameter."""


@dataclass
class OpeningSpec:
    """An opening of the room: which room-type entry it fills and where it sits.

    ``offset`` is the centre of the opening along edge ``edge``, measured from
    the edge's start vertex. ``hinge`` (``start`` or ``end``) puts the leaf of a
    door at that end; by default the leaf hangs at the end nearer a corner.
    """

    function: str
    edge: int
    offset: float
    component: str | None = None
    hinge: str | None = None
    entry: str | None = None


@dataclass
class Unplaced:
    entry_id: str
    index: int
    reason: str


@dataclass
class RoomLayoutResult:
    ifc_file: ifcopenshell.file
    space: ifcopenshell.entity_instance
    layout: rr.Layout
    issues: list[rr.RuleResult] = field(default_factory=list)
    unplaced: list[Unplaced] = field(default_factory=list)

    @property
    def required_issues(self) -> list[rr.RuleResult]:
        return [issue for issue in self.issues if issue.severity == "required"]


# ── Configuration ────────────────────────────────────────────────────────────


def _preset(config: dict[str, Any], name: str) -> Any:
    for preset in config.get("attribute_presets") or []:
        if preset.get("name") == name:
            return preset.get("value")
    return None


def _applies(entry: dict[str, Any], selection: dict[str, Iterable[str]] | None) -> bool:
    if not rr.condition_met(entry.get("when"), selection):
        return False
    return not (entry.get("unless") and rr.condition_met(entry["unless"], selection))


def _count(quantity: Any, room: rr.Room, config: dict[str, Any]) -> int:
    if isinstance(quantity, int):
        return quantity
    count = int(quantity.get("default", quantity["min"]))
    if "per" in quantity:
        per = quantity["per"]
        value = room.area if per["quantity"] == "net_floor_area" else float(_preset(config, "PeakOccupancy") or 0)
        count = math.ceil(value / float(per["divisor"]) - 1e-9)
    count = max(count, int(quantity["min"]))
    if "max" in quantity:
        count = min(count, int(quantity["max"]))
    return count


def _max_count(quantity: Any) -> int | None:
    if isinstance(quantity, int):
        return quantity
    return quantity.get("max")


def _dependencies(entry: dict[str, Any]) -> set[str]:
    functions: set[str] = set()
    for rule in entry.get("placement_rules") or []:
        for body in [rule, *(rule.get("variants") or [])]:
            function = (body.get("target") or {}).get("equipment_function")
            if function and function != entry["function"]:
                functions.add(function)
    return functions


def _anchors(entry: dict[str, Any]) -> int:
    """Required rules that tie an item to an opening or a wall; these leave few positions."""
    return sum(
        1
        for rule in entry.get("placement_rules") or []
        if rule["severity"] == "required"
        and rule["relation"] in rr.POSITIVE_RELATIONS
        and "equipment_function" not in (rule.get("target") or {})
    )


def _placement_order(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anchored entries first; entries whose rules point at other equipment come after that equipment."""
    present = {entry["function"] for entry in entries}
    ordered: list[dict[str, Any]] = []
    placed: set[str] = set()
    pending = sorted(entries, key=lambda e: (-_anchors(e), e["sort_order"]))
    while pending:
        ready = next(
            (e for e in pending if not (_dependencies(e) & present) - placed - {e["function"]}),
            pending[0],
        )
        pending.remove(ready)
        ordered.append(ready)
        placed.add(ready["function"])
    return ordered


# ── Openings ─────────────────────────────────────────────────────────────────


def _opening_size(component: dict[str, Any], params: dict[str, float]) -> tuple[float, float, float]:
    width = params.get("clear_width", params.get("width"))
    height = params.get("clear_height", params.get("height"))
    if width is None or height is None:
        raise ValueError(f"{component['id']}: opening needs width/clear_width and height/clear_height")
    elevation = component["placement"].get("elevation", 0.0)
    return float(width), float(height), rr.resolve_length(elevation, params)


def _place_opening(
    index: int,
    spec: OpeningSpec,
    room: rr.Room,
    config: dict[str, Any],
) -> rr.Placed:
    entries = [e for kind, e in rr.configuration_entries(config) if kind == "opening"]
    entry = next(
        (e for e in entries if (spec.entry and e["id"] == spec.entry) or (not spec.entry and e["function"] == spec.function)),
        None,
    )
    if entry is None:
        raise ValueError(f"no opening entry with function {spec.function!r} in {config['id']}")
    component_id = spec.component or entry["components"][0]
    component = rr.component(component_id)
    params = rr.component_parameters(component, entry.get("params"))
    width, height, elevation = _opening_size(component, params)
    edge_index = spec.edge
    offset = float(spec.offset)
    hinge = spec.hinge
    if room.reversed:
        edge_index = len(room.edges) - 1 - edge_index
        offset = room.edges[edge_index].length - offset
        hinge = {"start": "end", "end": "start"}.get(hinge or "", None)
    edge = room.edges[edge_index]
    t0, t1 = offset - width / 2.0, offset + width / 2.0
    if t0 < -rr.TOLERANCE or t1 > edge.length + rr.TOLERANCE:
        raise ValueError(f"opening {index} ({spec.function}) does not fit on edge {spec.edge}")
    thickness = WALL_THICKNESS.get(edge.kind, WALL_THICKNESS["interior"])
    frame = rr.Frame(edge.point_at(t0, -thickness), edge.direction, width, thickness)
    if component["category"] == "door" and hinge is None:
        hinge = "start" if offset <= edge.length / 2.0 else "end"
    return rr.Placed(
        key=f"opening-{index}",
        kind="opening",
        function=entry["function"],
        frame=frame,
        z_min=elevation,
        z_max=elevation + height,
        entry_id=entry["id"],
        component_id=component_id,
        clearances=rr.clearance_polygons(component, params, frame),
        edge_index=edge_index,
        hinge_end=hinge if component["category"] == "door" else None,
    )


# ── Equipment ────────────────────────────────────────────────────────────────


@dataclass
class _Template:
    entry: dict[str, Any]
    component: dict[str, Any]
    params: dict[str, float]
    width: float
    depth: float
    height: float
    elevation: float


def _template(entry: dict[str, Any], wall_height: float) -> _Template:
    component = rr.component(entry["components"][0])
    params = rr.component_parameters(component, entry.get("params"))
    width = params.get("width")
    depth = params.get("depth")
    if width is None or depth is None:
        raise ValueError(f"{component['id']}: equipment needs width and depth parameters")
    height = params.get("height", DEFAULT_HEIGHT)
    elevation = rr.resolve_length(component["placement"].get("elevation", 0.0), params)
    for rule in entry.get("placement_rules") or []:
        if rule["relation"] != "elevation":
            continue
        bounds = rule["value"]
        lo, hi = bounds.get("min", 0.0), bounds.get("max", wall_height - height)
        if not lo - rr.TOLERANCE <= elevation <= hi + rr.TOLERANCE:
            elevation = (lo + hi) / 2.0
    return _Template(entry, component, params, float(width), float(depth), float(height), float(elevation))


def _frames(template: _Template, room: rr.Room) -> list[rr.Frame]:
    placement = template.component["placement"]
    host = placement["host"]
    kinds = set(placement.get("edge_kinds") or ["interior", "exterior", "party_wall", "shaft"])
    margin = float(placement.get("side_distance_min", 0.0))
    w, d = template.width, template.depth
    frames: list[rr.Frame] = []
    for edge in room.edges:
        if host != "floor" and edge.kind not in kinds:
            continue
        last = edge.length - margin - w
        if last < margin - 1e-9:
            continue
        if host == "wall_corner":
            positions = [margin, last]
        else:
            steps = int(math.floor((last - margin) / WALL_STEP + 1e-9))
            positions = [margin + i * WALL_STEP for i in range(steps + 1)]
            if last - positions[-1] > 1e-6:
                positions.append(last)
        frames.extend(rr.Frame(edge.point_at(t), edge.direction, w, d) for t in positions)
    if host == "floor":
        fronts = sorted({(round(e.normal[0], 6), round(e.normal[1], 6)) for e in room.edges})
        x0, y0, x1, y1 = room.polygon.bounds
        nx = int((x1 - x0) / GRID_STEP)
        ny = int((y1 - y0) / GRID_STEP)
        for i in range(nx + 1):
            for j in range(ny + 1):
                centre = (x0 + i * GRID_STEP, y0 + j * GRID_STEP)
                for front in fronts:
                    frames.append(rr.Frame.facing(centre, front, w, d))
    return frames


def _z_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return min(a1, b1) - max(a0, b0) > rr.TOLERANCE


def _fits(candidate: rr.Placed, layout: rr.Layout, inside) -> bool:
    footprint = candidate.footprint
    if not inside.covers(footprint):
        return False
    if any(not inside.covers(zone) for zone in candidate.clearances):
        return False
    room = layout.room
    for other in layout.items:
        if other.kind == "opening":
            edge = room.edges[other.edge_index]
            t0, t1 = edge.interval(other.footprint)
            span = LineString([edge.point_at(t0), edge.point_at(t1)])
            a, b = edge.interval(footprint)
            if (
                footprint.distance(span) <= rr.WALL_TOLERANCE
                and min(b, t1) - max(a, t0) > rr.TOLERANCE
                and _z_overlap(candidate.z_min, candidate.z_max, other.z_min, other.z_max)
            ):
                return False
        elif footprint.intersection(other.footprint).area > rr.AREA_TOLERANCE and _z_overlap(
            candidate.z_min, candidate.z_max, other.z_min, other.z_max
        ):
            return False
        if any(footprint.intersection(zone).area > rr.AREA_TOLERANCE for zone in other.clearances):
            return False
        if any(other.footprint.intersection(zone).area > rr.AREA_TOLERANCE for zone in candidate.clearances):
            return False
    return True


def _score(
    candidate: rr.Placed,
    layout: rr.Layout,
    rules: list[tuple[dict[str, Any], list[rr.Target] | None]],
    siblings: list[rr.Placed],
) -> tuple[int, float, int, float, float]:
    required_failed = 0
    required_badness = 0.0
    preferred_met = 0
    preferred_badness = 0.0
    closeness = 0.0
    for rule, targets in rules:
        outcome = rr.evaluate_rule(rule, candidate, layout, targets)
        if rule["severity"] == "required":
            if not outcome.ok:
                required_failed += 1
                required_badness += min(outcome.badness, 1e6)
        else:
            if outcome.ok:
                preferred_met += 1
            else:
                preferred_badness += min(outcome.badness, 1e6)
        if outcome.ok and rule["relation"] in ("next_to", "distance_to") and isinstance(outcome.measured, float):
            closeness += outcome.measured
    heuristic = 0.01 * closeness
    if candidate.component_id and rr.component(candidate.component_id)["placement"]["host"] == "floor":
        heuristic += 0.0 if rr.host_edge(candidate, layout.room) else 1.0
    if siblings:
        spread = min(math.dist(candidate.centre, s.centre) for s in siblings)
        heuristic -= 0.1 * min(spread, 3.0)
    return (required_failed, required_badness, -preferred_met, preferred_badness, heuristic)


def _place_item(
    template: _Template,
    key: str,
    layout: rr.Layout,
    rules: list[tuple[dict[str, Any], list[rr.Target] | None]],
    siblings: list[rr.Placed],
    inside,
) -> tuple[rr.Placed | None, str]:
    best: tuple[tuple, rr.Placed] | None = None
    feasible = 0
    for frame in _frames(template, layout.room):
        candidate = rr.Placed(
            key=key,
            kind="equipment",
            function=template.entry["function"],
            frame=frame,
            z_min=template.elevation,
            z_max=template.elevation + template.height,
            entry_id=template.entry["id"],
            component_id=template.component["id"],
            clearances=rr.clearance_polygons(template.component, template.params, frame),
        )
        if not _fits(candidate, layout, inside):
            continue
        feasible += 1
        score = _score(candidate, layout, rules, siblings)
        if best is None or score < best[0]:
            best = (score, candidate)
    if best is None:
        return None, "no free position in the room"
    if best[0][0]:
        failed = [
            rule["id"]
            for rule, targets in rules
            if rule["severity"] == "required" and not rr.evaluate_rule(rule, best[1], layout, targets).ok
        ]
        return None, f"no free position meets required rules {', '.join(failed)} ({feasible} free positions tried)"
    return best[1], ""


def _place_entry(
    template: _Template,
    count: int,
    layout: rr.Layout,
    inside,
    unplaced: list[Unplaced],
) -> None:
    entry = template.entry
    rules = entry.get("placement_rules") or []
    item_rules = [(rule, None) for rule in rules if rule.get("scope") != "each_target"]
    target_rules = [rule for rule in rules if rule.get("scope") == "each_target"]
    limit = _max_count(entry["quantity"])
    placed: list[rr.Placed] = []

    def place(rule_set, reason_index: int) -> rr.Placed | None:
        key = f"{entry['id']}#{len(placed) + 1}"
        item, reason = _place_item(template, key, layout, rule_set, placed, inside)
        if item is None:
            unplaced.append(Unplaced(entry["id"], reason_index, reason))
            return None
        layout.items.append(item)
        placed.append(item)
        return item

    attempts = 0
    for rule in target_rules:
        for target in rr.resolve_targets(rule.get("target"), layout, None):
            if any(rr.evaluate_rule(rule, item, layout, [target]).ok for item in placed):
                continue
            if limit is not None and len(placed) >= limit:
                break
            attempts += 1
            place(item_rules + [(rule, [target])], attempts)
    while attempts < count and len(placed) < count:
        attempts += 1
        place(item_rules, attempts)


# ── IFC ──────────────────────────────────────────────────────────────────────


def _localized(value: Any, language: str) -> str | None:
    if isinstance(value, dict):
        return str(value.get(language) or next(iter(value.values())))
    return None if value is None else str(value)


def _frame_matrix(frame: rr.Frame, z: float):
    return axis_placement_matrix(
        (frame.origin[0], frame.origin[1], z),
        local_x=(frame.x_axis[0], frame.x_axis[1], 0.0),
        local_z=(0.0, 0.0, 1.0),
    )


def _box_product(
    ifc_file: ifcopenshell.file,
    body_context,
    item: rr.Placed,
    component: dict[str, Any],
    name: str,
    language: str,
):
    product = create_entity(
        ifc_file,
        ifc_class=rr.element_ifc_class(component),
        name=name,
        predefined_type=component.get("predefined_type"),
    )
    if component.get("object_type"):
        product.ObjectType = _localized(component["object_type"], language)
    edit_object_placement(ifc_file, product=product, matrix=_frame_matrix(item.frame, item.z_min))
    w, d = item.frame.width, item.frame.depth
    solid = create_extruded_area_solid(ifc_file, [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)], item.z_max - item.z_min)
    assign_representation(
        ifc_file, product=product, representation=create_body_representation(ifc_file, body_context, solid)
    )
    return product


def _wall_polyline(edge: rr.Edge, thickness: float) -> list[tuple[float, float]]:
    return [
        edge.point_at(-thickness, 0.0),
        edge.point_at(edge.length + thickness, 0.0),
        edge.point_at(edge.length + thickness, -thickness),
        edge.point_at(-thickness, -thickness),
    ]


def _write_ifc(
    layout: rr.Layout,
    config: dict[str, Any],
    room_type_data: dict[str, Any],
    *,
    space_name: str,
    wall_height: float,
    language: str,
    project_name: str,
):
    ifc_file, _project, _site, _building, storey, body_context = create_project_shell(project_name, storey_name="EG")
    body_context = get_body_context(ifc_file) or body_context
    room = layout.room
    long_name = _localized(_preset(config, "LongName"), language) or _localized(room_type_data["name"], language)
    space = _create_space_entity(
        ifc_file,
        storey=storey,
        body_context=body_context,
        name=space_name,
        long_name=long_name,
        predefined_type=str(_preset(config, "PredefinedType") or "SPACE"),
        polyline=room.outline,
        height=wall_height,
        quantities={"NetFloorArea": round(room.area, 3)},
    )
    walls = {}
    for edge in room.edges:
        thickness = WALL_THICKNESS.get(edge.kind, WALL_THICKNESS["interior"])
        wall = add_extruded_product(
            ifc_file,
            ifc_class="IfcWall",
            name=f"Wand {edge.index + 1}",
            body_context=body_context,
            storey=storey,
            polyline=_wall_polyline(edge, thickness),
            thickness=wall_height,
        )
        assign_pset(ifc_file, wall, "Pset_WallCommon", {"IsExternal": edge.kind == "exterior"})
        walls[edge.index] = wall

    counters: dict[str, int] = {}
    for item in layout.items:
        component = rr.component(item.component_id)
        counters[item.component_id] = counters.get(item.component_id, 0) + 1
        name = f"{_localized(component['name'], language)} {counters[item.component_id]}"
        product = _box_product(ifc_file, body_context, item, component, name, language)
        if item.kind == "opening":
            edge = room.edges[item.edge_index]
            opening = create_entity(ifc_file, ifc_class="IfcOpeningElement", name=f"Öffnung {name}")
            edit_object_placement(ifc_file, product=opening, matrix=translation_matrix(z=item.z_min))
            void = rr.Frame(item.frame.point(0.0, -0.01), item.frame.x_axis, item.frame.width, item.frame.depth + 0.02)
            solid = create_extruded_area_solid(ifc_file, list(void.footprint.exterior.coords)[:-1], item.z_max - item.z_min)
            assign_representation(
                ifc_file, product=opening, representation=create_body_representation(ifc_file, body_context, solid)
            )
            add_feature(ifc_file, feature=opening, element=walls[edge.index])
            add_filling(ifc_file, opening=opening, element=product)
            assign_container(ifc_file, relating_structure=storey, products=[product])
            if product.is_a("IfcDoor") and item.hinge_end:
                sliding = not any(c["side"] == "swing" for c in component.get("clearances") or [])
                product.OperationType = rr.operation_type(item.frame, item.hinge_end, edge, sliding=sliding)
        else:
            assign_container(ifc_file, relating_structure=space, products=[product])
        item.key = product.GlobalId
    layout.key = space.GlobalId
    return ifc_file, space


# ── Entry point ──────────────────────────────────────────────────────────────


def generate_room_layout(
    outline: Sequence[Sequence[float]],
    openings: Sequence[OpeningSpec | dict[str, Any]],
    room_type: str = "buero",
    *,
    configuration_id: str | None = None,
    edge_kinds: Sequence[str] | None = None,
    selection: dict[str, Iterable[str]] | None = None,
    space_name: str = "1.01",
    wall_height: float = 2.6,
    language: str = "de",
    project_name: str = "Raumlayout",
) -> RoomLayoutResult:
    """Place the equipment of ``room_type`` in a room and write it as IFC.

    ``outline`` is the room polygon in metres; ``edge_kinds`` gives one kind per
    edge (default: edges with a daylight or outdoor opening are ``exterior``, the
    rest ``interior``). ``selection`` holds the chosen ``project_goal_levels``
    and ``scenario_options`` for ``when``/``unless`` conditions.
    """
    room_type_data = rr.room_type(room_type)
    config = rr.configuration(room_type_data, configuration_id)
    specs = [spec if isinstance(spec, OpeningSpec) else OpeningSpec(**spec) for spec in openings]
    if edge_kinds is None:
        count = len(outline) - (1 if tuple(outline[0]) == tuple(outline[-1]) else 0)
        kinds = ["interior"] * count
        for spec in specs:
            if spec.function in ("daylight", "outdoor_access"):
                kinds[spec.edge] = "exterior"
        edge_kinds = kinds
    room = rr.Room(outline, edge_kinds)
    layout = rr.Layout(room, [_place_opening(i, spec, room, config) for i, spec in enumerate(specs, start=1)])

    inside = room.polygon.buffer(1e-6)
    unplaced: list[Unplaced] = []
    entries = [e for kind, e in rr.configuration_entries(config) if kind == "equipment" and _applies(e, selection)]
    for entry in _placement_order(entries):
        template = _template(entry, wall_height)
        _place_entry(template, _count(entry["quantity"], room, config), layout, inside, unplaced)

    ifc_file, space = _write_ifc(
        layout,
        config,
        room_type_data,
        space_name=space_name,
        wall_height=wall_height,
        language=language,
        project_name=project_name,
    )
    issues = rr.evaluate_layout(layout, config)
    return RoomLayoutResult(ifc_file, space, layout, issues, unplaced)
