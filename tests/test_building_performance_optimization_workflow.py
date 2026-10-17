"""Guard the early-operation building performance optimisation workflow."""

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/opr-building-performance-optimization"
LANGUAGES = ("de", "fr", "it", "en")
REQUIRED_LINKS = {
    "pragmaticbim:element/spaces-interior": {"Name", "LongName"},
    "pragmaticbim:element/architecture-door-exterior": {"Name"},
    "pragmaticbim:element/architecture-door-interior": {"Name"},
    "pragmaticbim:element/architecture-window-exterior": {"Name"},
    "pragmaticbim:element/architecture-window-interior": {"Name"},
    "pragmaticbim:element/mep-sensor": {"PredefinedType", "Tag"},
}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def _linked_attributes() -> dict[str, set[str]]:
    linked: dict[str, set[str]] = {}
    for path in sorted((REPO_ROOT / "elements").glob("*.yaml")):
        element = _load(path)
        for attribute in element.get("attributes") or []:
            if WORKFLOW_ID in (attribute.get("needed_for_workflows") or []):
                linked.setdefault(str(element["id"]), set()).add(
                    str(attribute["name"])
                )
    return linked


def test_workflow_is_active_localised_operation_workflow() -> None:
    workflow = _load(
        REPO_ROOT
        / "workflows"
        / "opr-building-performance-optimization.yaml"
    )

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/opr"
    assert {
        "pragmaticbim:domain/architecture",
        "pragmaticbim:domain/mep",
        "pragmaticbim:domain/building-physics",
    } <= set(workflow["needed_in_domain"])
    for language in LANGUAGES:
        assert str(workflow["name"][language]).strip()
        description = str(workflow["description"][language])
        assert "CO₂" in description
        assert "simul" in description.lower()


def test_workflow_has_minimal_spatial_and_sensor_references() -> None:
    linked = _linked_attributes()

    for element_id, attribute_names in REQUIRED_LINKS.items():
        assert attribute_names <= linked.get(element_id, set()), element_id


def test_facility_management_goal_activates_workflow() -> None:
    goal = _load(REPO_ROOT / "project_goals" / "facility-management.yaml")
    matching_levels = [
        level
        for level in goal.get("levels") or []
        if WORKFLOW_ID in (level.get("activated_workflows") or [])
    ]

    assert len(matching_levels) == 1
    assert matching_levels[0]["code"] == "OPS-04"
    assert matching_levels[0]["status"] == "active"


def test_sustainability_goal_activates_workflow_from_medium_level() -> None:
    goal = _load(
        REPO_ROOT / "project_goals" / "verifiable-sustainability.yaml"
    )
    levels_by_code = {
        str(level["code"]): level for level in goal.get("levels") or []
    }

    assert WORKFLOW_ID not in levels_by_code["SUS-01"]["activated_workflows"]
    assert WORKFLOW_ID in levels_by_code["SUS-02"]["activated_workflows"]
    assert WORKFLOW_ID in levels_by_code["SUS-03"]["activated_workflows"]


def test_handover_introduction_names_the_performance_gap() -> None:
    handover = _load(REPO_ROOT / "workflows" / "hov.yaml")

    assert "Performance Gap" in handover["description"]["de"]
    for language in LANGUAGES:
        assert len(str(handover["description"][language]).split()) >= 40
