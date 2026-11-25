"""Mix goals activate unit types, and scenario options place their rooms in units through `target`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

# Room-adding options of `unit` scenarios that deliberately place their rooms in the building.
UNIT_OPTIONS_WITHOUT_TARGET = {
    # The variant offers a shared office in the building instead of a room in the unit.
    "pragmaticbim:scenario-option/arbeiten-von-zuhause-community-office",
}


def _load_dir(folder: str) -> list[dict[str, Any]]:
    items = []
    for path in sorted((REPO_ROOT / folder).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        items.append(data)
    return items


@lru_cache(maxsize=1)
def _room_types() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in _load_dir("room_types")}


@lru_cache(maxsize=1)
def _goals() -> list[dict[str, Any]]:
    return _load_dir("project_goals")


@lru_cache(maxsize=1)
def _scenarios() -> list[dict[str, Any]]:
    return _load_dir("usage_scenarios")


def _options() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(scenario, option) for scenario in _scenarios() for option in scenario.get("options") or []]


def _base(room_id: str) -> str:
    return _room_types()[room_id].get("extends") or room_id


def _activations() -> list[tuple[dict[str, Any], dict[str, Any], str]]:
    return [
        (goal, level, room_id)
        for goal in _goals()
        for level in goal.get("levels") or []
        for room_id in level.get("activated_room_types") or []
    ]


def _targets() -> set[str]:
    return {option["target"] for _, option in _options() if option.get("target")}


def test_activated_room_types_are_units_of_the_goal_use() -> None:
    assert _activations()
    for goal, level, room_id in _activations():
        assert goal.get("is_boundary_condition") is True, f"{goal['id']}: only a boundary mix goal activates units"
        room_type = _room_types().get(room_id)
        assert room_type, f"{level['id']}: unknown room type {room_id}"
        assert room_type.get("room_type_kind") == "container", f"{level['id']}: {room_id} is not a unit type"
        assert set(room_type["uses"]) <= set(goal.get("uses") or []), (
            f"{level['id']}: {room_id} belongs to {room_type['uses']}, not to the goal's uses"
        )


@pytest.mark.parametrize("option_id", sorted({o["id"] for _, o in _options() if o.get("target")}))
def test_target_is_a_base_unit_of_the_scenario_use(option_id: str) -> None:
    scenario, option = next((s, o) for s, o in _options() if o["id"] == option_id)
    target = _room_types().get(option["target"])
    assert target, f"{option_id}: unknown target {option['target']}"
    assert target.get("room_type_kind") == "container", f"{option_id}: target is not a unit type"
    assert "extends" not in target, f"{option_id}: target the base unit type, not a size"
    uses = option.get("uses") or scenario["uses"]
    assert set(target["uses"]) <= set(uses), f"{option_id}: target use {target['uses']} not in {uses}"
    assert option.get("adds"), f"{option_id}: a target without adds places nothing"


def test_every_activated_unit_has_a_targeted_base() -> None:
    targets = _targets()
    for _, level, room_id in _activations():
        base = _base(room_id)
        assert "extends" not in _room_types()[base], f"{room_id}: extends a size, not a base"
        assert base in targets, f"{level['id']}: no scenario option places rooms in {base}"


def test_unit_scenario_options_target_a_unit() -> None:
    for scenario, option in _options():
        if scenario.get("scope") != "unit" or not option.get("adds"):
            continue
        if option["id"] in UNIT_OPTIONS_WITHOUT_TARGET:
            assert not option.get("target"), f"{option['id']}: remove it from UNIT_OPTIONS_WITHOUT_TARGET"
            continue
        assert option.get("target"), f"{option['id']}: a unit scenario places its rooms in a unit; set target"
