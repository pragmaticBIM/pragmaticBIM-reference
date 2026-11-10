"""Usage scenario scope, the uses a scenario applies to, and the use of each unit type."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPES = {"project", "use", "unit"}
ROOM_SCOPES = {"site", "building", "unit"}

# Rooms a `unit` scenario may add although their default scope is not `unit`, keyed by option id.
UNIT_SCENARIO_EXCEPTIONS: dict[str, set[str]] = {
    # The variant offers a shared office in the building instead of a room in the unit.
    "pragmaticbim:scenario-option/arbeiten-von-zuhause-community-office": {
        "pragmaticbim:room-type/gemeinschaftsbuero",
    },
    # Hotelzimmer is the main room of every Beherbergung unit type.
    "pragmaticbim:scenario-option/in-der-beherbergung-uebernachten-room": {
        "pragmaticbim:room-type/hotelzimmer",
    },
    "pragmaticbim:scenario-option/in-der-beherbergung-uebernachten-living": {
        "pragmaticbim:room-type/hotelzimmer",
    },
}


def _load_dir(folder: str) -> list[dict[str, Any]]:
    items = []
    for path in sorted((REPO_ROOT / folder).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        items.append(data)
    return items


@lru_cache(maxsize=1)
def _scenarios() -> list[dict[str, Any]]:
    return _load_dir("usage_scenarios")


@lru_cache(maxsize=1)
def _room_types() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in _load_dir("room_types")}


@lru_cache(maxsize=1)
def _uses() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in _load_dir("uses")}


def _ids(items: list[dict[str, Any]]) -> list[str]:
    return [item["id"] for item in items]


@pytest.mark.parametrize("scenario", _scenarios(), ids=_ids(_scenarios()))
def test_scenario_has_scope_and_uses(scenario: dict[str, Any]) -> None:
    assert scenario.get("scope") in SCOPES, f"{scenario['id']}: scope must be one of {sorted(SCOPES)}"
    assert "use" not in scenario, f"{scenario['id']}: use `uses: [...]` instead of `use`"
    uses = scenario.get("uses")
    assert isinstance(uses, list) and uses, f"{scenario['id']}: uses must list at least one use"
    assert len(uses) == len(set(uses)), f"{scenario['id']}: duplicate entry in uses"
    for use in uses:
        assert use in _uses(), f"{scenario['id']}: unknown use {use}"
        assert _uses()[use].get("status") != "deprecated", f"{scenario['id']}: deprecated use {use}"


def test_room_type_scope_values() -> None:
    for room_type in _room_types().values():
        scope = room_type.get("default_scope")
        assert scope is None or scope in ROOM_SCOPES, f"{room_type['id']}: default_scope {scope!r}"


@pytest.mark.parametrize(
    "scenario",
    [s for s in _scenarios() if s.get("scope") == "unit"],
    ids=_ids([s for s in _scenarios() if s.get("scope") == "unit"]),
)
def test_unit_scenario_adds_only_unit_rooms(scenario: dict[str, Any]) -> None:
    for option in scenario.get("options") or []:
        allowed = UNIT_SCENARIO_EXCEPTIONS.get(option["id"], set())
        for room in option.get("adds") or []:
            scope = _room_types()[room].get("default_scope")
            assert scope == "unit" or room in allowed, (
                f"{option['id']}: adds {room} with scope {scope!r}; a unit scenario adds unit rooms only"
            )


def test_unit_scenario_exceptions_are_current() -> None:
    options = {
        option["id"]: option
        for scenario in _scenarios()
        if scenario.get("scope") == "unit"
        for option in scenario.get("options") or []
    }
    for option_id, rooms in UNIT_SCENARIO_EXCEPTIONS.items():
        assert option_id in options, f"{option_id}: exception for an option that is not in a unit scenario"
        added = set(options[option_id].get("adds") or [])
        for room in rooms:
            assert room in added, f"{option_id}: exception for {room}, which the option does not add"
            assert _room_types()[room].get("default_scope") != "unit", f"{option_id}: {room} needs no exception"


def test_unit_types_have_exactly_one_use() -> None:
    for room_type in _room_types().values():
        if room_type.get("room_type_kind") != "container":
            continue
        uses = room_type.get("uses") or []
        assert len(uses) == 1, f"{room_type['id']}: a unit type lists exactly one use, got {uses}"
