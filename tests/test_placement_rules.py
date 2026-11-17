"""Placement rules on room-type equipment: data, shared evaluation, generator and checker."""

from __future__ import annotations

from typing import Any

import ifcopenshell
import ifcopenshell.util.placement
import numpy as np
import pytest
from ifcopenshell.api.geometry import edit_object_placement
from ifcopenshell.api.spatial import assign_container, reference_structure

from checks.placement_rules import check_placement_rules, resolve_room_type
from generators import room_rules as rr
from generators.room_layout import OpeningSpec, generate_room_layout

BUERO = "pragmaticbim:room-type/buero"
SWITCH_ENTRY = "pragmaticbim:room-type-equipment/buero-default-lichtschalter"
OUTLET_ENTRY = "pragmaticbim:room-type-equipment/buero-default-steckdose"
WORKPLACE_ENTRY = "pragmaticbim:room-type-equipment/buero-default-arbeitsplatz"
RULE = "pragmaticbim:placement-rule/"


# ── Data ─────────────────────────────────────────────────────────────────────


def _configurations():
    for room_type in rr.room_types().values():
        for config in room_type.get("configurations") or []:
            yield room_type, config


def test_placement_rule_ids_are_unique_and_named_after_their_entry() -> None:
    seen: set[str] = set()
    for _, config in _configurations():
        for _, entry in rr.configuration_entries(config):
            slug = entry["id"].split("/")[-1]
            for rule in entry.get("placement_rules") or []:
                assert rule["id"].startswith(f"{RULE}{slug}-"), rule["id"]
                assert rule["id"] not in seen, f"duplicate rule id {rule['id']}"
                seen.add(rule["id"])


def test_placement_rule_targets_exist_in_their_configuration() -> None:
    for _, config in _configurations():
        functions = {
            "equipment_function": {e["function"] for e in config.get("equipment") or []},
            "opening_function": {e["function"] for e in config.get("openings") or []},
        }
        for _, entry in rr.configuration_entries(config):
            for rule in entry.get("placement_rules") or []:
                for body in [rule, *(rule.get("variants") or [])]:
                    for key, value in (body.get("target") or {}).items():
                        if key in functions:
                            assert value in functions[key], f"{rule['id']}: no {key} {value} in {config['id']}"
                    if body.get("side"):
                        function = body["target"]["opening_function"]
                        doors = [
                            e for e in config.get("openings") or []
                            if e["function"] == function
                            and any(rr.component(c)["category"] == "door" for c in e["components"])
                        ]
                        assert doors, f"{rule['id']}: {body['side']} needs a door"
                if rule.get("scope") == "each_target":
                    assert "edge_kind" not in rule["target"], rule["id"]


def test_buero_has_rules_on_every_entry() -> None:
    config = rr.configuration(rr.room_type(BUERO))
    entries = list(rr.configuration_entries(config))
    functions = {entry["function"] for _, entry in entries}
    assert {"power_outlet", "light_switch"} <= functions
    for _, entry in entries:
        assert entry.get("placement_rules"), f"{entry['id']} has no placement rules"


# ── Shared evaluation: one positive and one negative case per relation ───────

ROOM = rr.Room([(0, 0), (4, 0), (4, 3), (0, 3)], ["interior", "interior", "exterior", "interior"])
DOOR_COMPONENT = rr.component("pragmaticbim:component/tuer-dreh-innen")


def _rule(relation: str, target: dict[str, str] | None = None, **fields: Any) -> dict[str, Any]:
    rule = {"id": f"{RULE}test-{relation.replace('_', '-')}", "relation": relation, "severity": "required"}
    if target is not None:
        rule["target"] = target
    rule.update(fields)
    return rule


def _door(hinge: str = "start") -> rr.Placed:
    edge = ROOM.edges[0]
    frame = rr.Frame(edge.point_at(0.3, -0.12), edge.direction, 0.8, 0.12)
    params = rr.component_parameters(DOOR_COMPONENT)
    return rr.Placed(
        "door", "opening", "access", frame, 0.0, 2.0,
        clearances=rr.clearance_polygons(DOOR_COMPONENT, params, frame),
        edge_index=0, hinge_end=hinge,
    )


def _window() -> rr.Placed:
    edge = ROOM.edges[2]
    frame = rr.Frame(edge.point_at(1.4, -0.3), edge.direction, 1.2, 0.3)
    return rr.Placed("window", "opening", "daylight", frame, 0.9, 2.3, edge_index=2)


def _on_wall(key: str, function: str, edge: int, t: float, *, z: float = 0.0, width: float = 0.08,
             depth: float = 0.03, height: float = 0.08) -> rr.Placed:
    e = ROOM.edges[edge]
    return rr.Placed(key, "equipment", function, rr.Frame(e.point_at(t), e.direction, width, depth), z, z + height)


def _desk(key: str, centre: tuple[float, float], front: tuple[float, float]) -> rr.Placed:
    return rr.Placed(key, "equipment", "working", rr.Frame.facing(centre, front, 1.6, 0.8), 0.0, 0.74)


def _layout(*items: rr.Placed) -> rr.Layout:
    return rr.Layout(ROOM, [_door(), _window(), *items])


def _check(rule: dict[str, Any], subject: rr.Placed, *others: rr.Placed) -> rr.Outcome:
    return rr.evaluate_rule(rule, subject, _layout(subject, *others))


def test_next_to_positive_and_negative() -> None:
    rule = _rule("next_to", {"equipment_function": "working"}, distance={"max": 1.0})
    desk = _desk("desk", (2.0, 2.6), (0.0, -1.0))
    assert _check(rule, _on_wall("near", "power_outlet", 2, 0.6, z=0.3), desk).ok
    far = _check(rule, _on_wall("far", "power_outlet", 0, 2.0, z=0.3), desk)
    assert not far.ok and far.measured == pytest.approx(2.17, abs=0.01)


def test_next_to_latch_side() -> None:
    rule = _rule("next_to", {"opening_function": "access"}, side="latch_side", distance={"max": 0.3})
    # Door spans t 0.3–1.1 on edge 0, hinge at the start: the latch jamb is at t = 1.1.
    assert _check(rule, _on_wall("latch", "light_switch", 0, 1.2, z=1.0)).ok
    hinge = _check(rule, _on_wall("hinge", "light_switch", 0, 0.1, z=1.0))
    assert not hinge.ok and "latch_side" in hinge.note
    moved = _check(rule, _on_wall("moved", "light_switch", 0, 2.1, z=1.0))
    assert not moved.ok and moved.measured == pytest.approx(1.0)
    hinge_rule = _rule("next_to", {"opening_function": "access"}, side="hinge_side", distance={"max": 0.3})
    assert _check(hinge_rule, _on_wall("hinge", "light_switch", 0, 0.1, z=1.0)).ok


def test_opposite_positive_and_negative() -> None:
    rule = _rule("opposite", {"opening_function": "daylight"})
    assert _check(rule, _on_wall("cab", "storage", 0, 2.0, width=0.8, depth=0.45)).ok
    side = _check(rule, _on_wall("cab", "storage", 1, 1.0, width=0.8, depth=0.45))
    assert not side.ok and side.measured == pytest.approx(90.0)


def test_same_wall_as_positive_and_negative() -> None:
    rule = _rule("same_wall_as", {"opening_function": "daylight"})
    assert _check(rule, _on_wall("cab", "storage", 2, 0.2, width=0.8, depth=0.45)).ok
    assert not _check(rule, _on_wall("cab", "storage", 0, 2.0, width=0.8, depth=0.45)).ok
    free = _check(rule, _desk("desk", (2.0, 1.5), (0.0, 1.0)))
    assert not free.ok and free.measured == "no wall"


def test_same_wall_as_edge_kind() -> None:
    rule = _rule("same_wall_as", {"edge_kind": "exterior"})
    assert _check(rule, _on_wall("cab", "storage", 2, 0.2, width=0.8, depth=0.45)).ok
    assert not _check(rule, _on_wall("cab", "storage", 1, 0.2, width=0.8, depth=0.45)).ok


def test_not_on_wall_with_positive_and_negative() -> None:
    rule = _rule("not_on_wall_with", {"opening_function": "daylight"})
    assert _check(rule, _on_wall("cab", "storage", 1, 1.0, width=0.8, depth=0.45)).ok
    window_wall = _check(rule, _on_wall("cab", "storage", 2, 0.2, width=0.8, depth=0.45))
    assert not window_wall.ok and window_wall.measured == "edge 2 (exterior)"
    door = rr.evaluate_rule(_rule("not_on_wall_with", {"edge_kind": "exterior"}), _door(), _layout())
    assert door.ok


def test_distance_to_positive_and_negative() -> None:
    rule = _rule("distance_to", {"opening_function": "daylight"}, distance={"max": 2.5})
    assert _check(rule, _desk("desk", (2.0, 2.6), (0.0, -1.0))).ok
    far = _check(rule, _desk("desk", (0.6, 0.4), (0.0, 1.0)))
    assert not far.ok and far.measured == pytest.approx(np.hypot(1.4, 2.6), abs=0.01)
    at_least = _rule("distance_to", {"opening_function": "daylight"}, distance={"min": 1.0})
    assert not _check(at_least, _desk("desk", (2.0, 2.6), (0.0, -1.0))).ok


def test_facing_positive_and_negative() -> None:
    rule = _rule("facing", {"opening_function": "daylight"})
    assert _check(rule, _desk("desk", (2.0, 1.0), (0.0, 1.0))).ok
    away = _check(rule, _desk("desk", (2.0, 1.0), (0.0, -1.0)))
    assert not away.ok and away.measured == pytest.approx(180.0)


def test_elevation_positive_and_negative() -> None:
    rule = _rule("elevation", value={"min": 0.9, "max": 1.1})
    assert _check(rule, _on_wall("switch", "light_switch", 0, 1.2, z=1.0)).ok
    low = _check(rule, _on_wall("switch", "light_switch", 0, 1.2, z=0.3))
    assert not low.ok and low.measured == pytest.approx(0.3)


def test_not_in_clearance_of_positive_and_negative() -> None:
    rule = _rule("not_in_clearance_of", {"opening_function": "access"})
    assert _check(rule, _on_wall("outlet", "power_outlet", 0, 2.0, z=0.3)).ok
    behind_door = _check(rule, _on_wall("outlet", "power_outlet", 0, 0.6, z=0.3))
    assert not behind_door.ok and behind_door.measured > 0
    desk = _check(rule, _desk("desk", (0.9, 0.5), (0.0, 1.0)))
    assert not desk.ok


def test_missing_target() -> None:
    layout = rr.Layout(ROOM, [])
    switch = _on_wall("switch", "light_switch", 0, 1.2, z=1.0)
    layout.items.append(switch)
    positive = rr.evaluate_rule(_rule("next_to", {"opening_function": "access"}, distance={"max": 0.3}), switch, layout)
    assert not positive.ok and positive.note == "no target in the room"
    assert rr.evaluate_rule(_rule("not_in_clearance_of", {"opening_function": "access"}), switch, layout).ok


def test_variant_accepts_switch_outside_the_room() -> None:
    body = {"target": {"opening_function": "access"}, "side": "latch_side", "distance": {"max": 0.3}}
    rule = _rule("next_to", **body, variants=[{"relation": "next_to", **body, "room_side": "outside"}])
    edge = ROOM.edges[0]
    outside = rr.Placed("switch", "equipment", "light_switch", rr.Frame(edge.point_at(1.3, -0.12), (-1.0, 0.0), 0.08, 0.03), 1.0, 1.08)
    without_variant = {k: v for k, v in rule.items() if k != "variants"}
    assert not _check(without_variant, outside).ok
    passed = _check(rule, outside)
    assert passed.ok and passed.note == "variant 1"


def test_each_target_scope_reports_the_unserved_target() -> None:
    config = {
        "id": "test",
        "equipment": [
            {"id": "e-desk", "function": "working", "components": [], "status": "active"},
            {
                "id": "e-outlet", "function": "power_outlet", "components": [], "status": "active",
                "placement_rules": [
                    _rule("next_to", {"equipment_function": "working"}, distance={"max": 1.0}, scope="each_target")
                ],
            },
        ],
    }
    near, far = _desk("near", (2.0, 2.6), (0.0, -1.0)), _desk("far", (2.0, 0.4), (0.0, 1.0))
    outlet = _on_wall("outlet", "power_outlet", 2, 0.6, z=0.3)
    for item, entry in ((near, "e-desk"), (far, "e-desk"), (outlet, "e-outlet")):
        item.entry_id = entry
    results = rr.evaluate_layout(_layout(near, far, outlet), config)
    assert [(r.element, r.ok) for r in results] == [("far", False)]


def test_room_keeps_edge_kinds_when_outline_is_clockwise() -> None:
    room = rr.Room([(0, 0), (0, 3), (4, 3), (4, 0)], ["interior", "exterior", "interior", "interior"])
    assert room.reversed
    exterior = [edge for edge in room.edges if edge.kind == "exterior"]
    assert len(exterior) == 1 and {exterior[0].start, exterior[0].end} == {(0.0, 3.0), (4.0, 3.0)}


# ── Generator and checker ────────────────────────────────────────────────────

OUTLINE = [(0, 0), (4, 0), (4, 3), (0, 3)]
OPENINGS = [OpeningSpec("access", edge=0, offset=0.7), OpeningSpec("daylight", edge=2, offset=2.0)]


@pytest.fixture(scope="module")
def buero():
    return generate_room_layout(OUTLINE, OPENINGS, "buero")


def _copy(result) -> ifcopenshell.file:
    return ifcopenshell.file.from_string(result.ifc_file.to_string())


def _item(result, entry_id: str) -> rr.Placed:
    return next(item for item in result.layout.items if item.entry_id == entry_id)


def _move(ifc_file: ifcopenshell.file, guid: str, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> None:
    product = ifc_file.by_guid(guid)
    matrix = ifcopenshell.util.placement.get_local_placement(product.ObjectPlacement)
    matrix[:3, 3] += (dx, dy, dz)
    edit_object_placement(ifc_file, product=product, matrix=matrix)


def test_generator_places_every_buero_item(buero) -> None:
    assert buero.unplaced == []
    assert buero.issues == []
    counts: dict[str, int] = {}
    for item in buero.layout.items:
        counts[item.function] = counts.get(item.function, 0) + 1
    # 12 m²: two workplaces (6 m² each), two outlets (10 m² each, at least one per workplace).
    assert counts == {"access": 1, "daylight": 1, "working": 2, "storage": 1, "power_outlet": 2, "light_switch": 1}
    ifc_file = buero.ifc_file
    assert len(ifc_file.by_type("IfcFurniture")) == 3
    assert len(ifc_file.by_type("IfcOutlet")) == 2
    assert len(ifc_file.by_type("IfcSwitchingDevice")) == 1
    assert ifc_file.by_type("IfcDoor")[0].OperationType == "SINGLE_SWING_LEFT"


def test_round_trip_has_no_required_violations(buero) -> None:
    results = check_placement_rules(_copy(buero), include_passed=True)
    assert results, "checker evaluated no rules"
    assert {r.space for r in results} == {buero.space.GlobalId}
    assert [r for r in results if not r.ok and r.severity == "required"] == []
    evaluated = {r.rule_id for r in results}
    config = rr.configuration(rr.room_type(BUERO))
    expected = {rule["id"] for _, e in rr.configuration_entries(config) for rule in e.get("placement_rules") or []}
    assert evaluated == expected


def test_generator_and_checker_agree_on_measurements(buero) -> None:
    generated = {(r.rule_id, r.element): r.measured for r in rr.evaluate_layout(buero.layout, rr.configuration(rr.room_type(BUERO)), include_passed=True)}
    checked = {(r.rule_id, r.element): r.measured for r in check_placement_rules(_copy(buero), include_passed=True)}
    assert generated.keys() == checked.keys()
    for key, value in generated.items():
        if isinstance(value, float):
            assert checked[key] == pytest.approx(value, abs=0.01), key


def test_checker_reports_switch_moved_away_from_the_door(buero) -> None:
    ifc_file = _copy(buero)
    switch = _item(buero, SWITCH_ENTRY)
    _move(ifc_file, switch.key, dx=1.0)
    violations = [r for r in check_placement_rules(ifc_file) if r.element == switch.key]
    assert len(violations) == 1
    violation = violations[0]
    assert violation.rule_id == f"{RULE}buero-default-lichtschalter-tuer"
    assert violation.severity == "required"
    assert violation.measured == pytest.approx(1.0, abs=0.01)


def test_checker_reports_raised_outlet_and_desk_in_door_swing(buero) -> None:
    ifc_file = _copy(buero)
    outlet = _item(buero, OUTLET_ENTRY)
    _move(ifc_file, outlet.key, dz=0.3)
    desk = _item(buero, WORKPLACE_ENTRY)
    product = ifc_file.by_guid(desk.key)
    matrix = np.eye(4)
    matrix[:3, 3] = (0.3, 0.1, 0.0)
    edit_object_placement(ifc_file, product=product, matrix=matrix)
    found = {(r.rule_id, r.element): r for r in check_placement_rules(ifc_file)}
    raised = found[(f"{RULE}buero-default-steckdose-hoehe", outlet.key)]
    assert raised.measured == pytest.approx(0.6, abs=0.01)
    swing = found[(f"{RULE}buero-default-arbeitsplatz-tuer-frei", desk.key)]
    assert swing.severity == "required" and swing.measured > 0


def test_checker_accepts_switch_outside_next_to_the_door(buero) -> None:
    ifc_file = _copy(buero)
    switch = _item(buero, SWITCH_ENTRY)
    # Through the 12 cm wall onto the corridor face, turned to face the corridor.
    product = ifc_file.by_guid(switch.key)
    matrix = ifcopenshell.util.placement.get_local_placement(product.ObjectPlacement)
    matrix[:3, 0], matrix[:3, 1] = -matrix[:3, 0], -matrix[:3, 1]
    matrix[:3, 3] += (0.08, -0.12, 0.0)
    edit_object_placement(ifc_file, product=product, matrix=matrix)
    space = ifc_file.by_guid(buero.space.GlobalId)
    corridor_storey = ifc_file.by_type("IfcBuildingStorey")[0]
    assign_container(ifc_file, products=[product], relating_structure=corridor_storey)
    reference_structure(ifc_file, products=[product], relating_structure=space)
    results = {r.rule_id: r for r in check_placement_rules(ifc_file, include_passed=True) if r.element == switch.key}
    assert results[f"{RULE}buero-default-lichtschalter-tuer"].ok


def test_checker_resolves_room_type_and_skips_unknown_spaces(buero) -> None:
    ifc_file = _copy(buero)
    space = ifc_file.by_guid(buero.space.GlobalId)
    assert resolve_room_type(space)["id"] == BUERO
    space.LongName = "Unbekannt"
    assert resolve_room_type(space) is None
    assert check_placement_rules(ifc_file) == []
    assert check_placement_rules(ifc_file, {space.GlobalId: "buero"}, include_passed=True)


def test_generator_reports_rules_it_cannot_meet() -> None:
    # The door's latch jamb sits in the corner: no wall is left beside it for the switch.
    openings = [
        OpeningSpec("access", edge=0, offset=3.6, hinge="start"),
        OpeningSpec("daylight", edge=2, offset=2.0),
    ]
    result = generate_room_layout(OUTLINE, openings, "buero")
    unplaced = [u for u in result.unplaced if u.entry_id == SWITCH_ENTRY]
    assert len(unplaced) == 1
    assert f"{RULE}buero-default-lichtschalter-tuer" in unplaced[0].reason
    assert not result.ifc_file.by_type("IfcSwitchingDevice")


def test_generator_handles_l_shaped_rooms() -> None:
    outline = [(0, 0), (5, 0), (5, 2.5), (2.5, 2.5), (2.5, 5), (0, 5)]
    openings = [OpeningSpec("access", edge=1, offset=1.0), OpeningSpec("daylight", edge=4, offset=1.2)]
    result = generate_room_layout(outline, openings, "buero")
    assert result.unplaced == []
    assert result.required_issues == []
    assert [r for r in check_placement_rules(_copy(result)) if r.severity == "required"] == []
