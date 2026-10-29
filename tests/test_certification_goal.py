"""Guard multiple choice on project goals and the certification goal."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
GOALS_DIR = REPO_ROOT / "project_goals"
LEVEL = "pragmaticbim:project-goal-level/"
NONE = LEVEL + "certification-none"
MINERGIE_ECO = LEVEL + "certification-minergie-eco"
SNBS = LEVEL + "certification-snbs"
DGNB = LEVEL + "certification-dgnb-sgni"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _goals() -> dict[str, dict[str, Any]]:
    return {path.name: _load_yaml(path) for path in sorted(GOALS_DIR.glob("*.yaml"))}


def _is_valid_selection(goal: dict[str, Any], picked: set[str]) -> bool:
    levels = {level["id"]: level for level in goal["levels"]}
    assert picked <= set(levels)
    if len(picked) <= 1:
        return True
    if not goal.get("allows_multiple", False):
        return False
    return not any(levels[level_id].get("exclusive", False) for level_id in picked)


def test_multiple_choice_fields_are_consistent() -> None:
    for name, goal in _goals().items():
        allows_multiple = goal.get("allows_multiple", False)
        assert isinstance(allows_multiple, bool), name
        for level in goal["levels"]:
            exclusive = level.get("exclusive", False)
            assert isinstance(exclusive, bool), level["id"]
            if exclusive:
                assert allows_multiple, f"{level['id']} is exclusive on a single-choice goal"


def test_certification_allows_combined_labels() -> None:
    goal = _load_yaml(GOALS_DIR / "certification.yaml")

    assert goal["allows_multiple"] is True
    assert _is_valid_selection(goal, {MINERGIE_ECO, SNBS})
    assert _is_valid_selection(goal, {MINERGIE_ECO, SNBS, DGNB})


def test_certification_none_cannot_be_combined() -> None:
    goal = _load_yaml(GOALS_DIR / "certification.yaml")
    levels = {level["id"]: level for level in goal["levels"]}

    assert levels[NONE]["exclusive"] is True
    assert [level_id for level_id, level in levels.items() if level.get("exclusive")] == [NONE]
    assert _is_valid_selection(goal, {NONE})
    for other in set(levels) - {NONE}:
        assert not _is_valid_selection(goal, {NONE, other})


def test_energy_standard_stays_single_choice() -> None:
    goal = _load_yaml(GOALS_DIR / "energy-standard.yaml")

    assert not goal.get("allows_multiple", False)
    assert not _is_valid_selection(
        goal,
        {LEVEL + "energy-standard-minergie", LEVEL + "energy-standard-minergie-p"},
    )


def test_combined_labels_imply_one_level_per_single_choice_goal() -> None:
    goals = _goals()
    goal_of_level = {
        level["id"]: goal for goal in goals.values() for level in goal["levels"]
    }
    certification = goals["certification.yaml"]
    labels = [level for level in certification["levels"] if not level.get("exclusive")]

    for size in range(2, len(labels) + 1):
        for combo in combinations(labels, size):
            implied: dict[str, set[str]] = {}
            for label in combo:
                for level_id in label.get("implied_levels", []):
                    implied.setdefault(goal_of_level[level_id]["id"], set()).add(level_id)
            for goal_id, level_ids in implied.items():
                goal = next(g for g in goals.values() if g["id"] == goal_id)
                assert _is_valid_selection(goal, level_ids), (
                    [label["id"] for label in combo],
                    goal_id,
                    level_ids,
                )
