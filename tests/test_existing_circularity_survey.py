"""Guard circularity procurement for existing buildings and its requirements."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from catalog.baseline import attribute_applies_to_all_workflows


REPO_ROOT = Path(__file__).resolve().parents[1]
ELEMENTS_DIR = REPO_ROOT / "elements"
WORKFLOW_ID = "pragmaticbim:workflow/bes-existing-circularity-procurement"
LANGUAGES = {"de", "fr", "it", "en"}

TARGET_ELEMENTS = {
    "architecture-column",
    "architecture-door-exterior",
    "architecture-door-interior",
    "architecture-floor-covering",
    "architecture-roof-pitched",
    "architecture-slab-balcony",
    "architecture-slab-base",
    "architecture-slab-flat-roof",
    "architecture-slab-floor",
    "architecture-wall-cladding-exterior",
    "architecture-wall-cladding-interior",
    "architecture-wall-exterior",
    "architecture-wall-interior",
    "architecture-wall-interior-loadbearing",
    "architecture-window-exterior",
    "architecture-window-interior",
}

REQUIREMENTS = {
    "Reuse": {
        "pset": "ePset_Circularity",
        "datatype": "IfcReal",
        "allowed_values": None,
    },
    "WasteCodes": {
        "pset": "ePset_Circularity",
        "datatype": "IfcText",
        "allowed_values": None,
    },
    "HazardType": {
        "pset": "ePset_HazardousMaterial",
        "datatype": "IfcText",
        "allowed_values": "pragmaticbim:value/hazard-type",
    },
    "RemovalCategory": {
        "pset": "ePset_HazardousMaterial",
        "datatype": "IfcText",
        "allowed_values": "pragmaticbim:value/removal-category",
    },
}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path}: expected a YAML mapping"
    return data


def test_existing_circularity_is_an_active_procurement_workflow() -> None:
    workflow = _load(
        REPO_ROOT / "workflows" / "bes-existing-circularity-procurement.yaml"
    )

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/bes"
    assert workflow["status"] == "active"
    assert set(workflow["name"]) == LANGUAGES
    assert set(workflow["description"]) == LANGUAGES
    assert "pragmaticbim:domain/architecture" in workflow["needed_in_domain"]


def test_survey_requires_four_attributes_on_each_target_element() -> None:
    linked_elements: set[str] = set()
    catalog_workflows = [
        _load(path)
        for path in sorted((REPO_ROOT / "workflows").glob("*.yaml"))
    ]

    for path in sorted(ELEMENTS_DIR.glob("*.yaml")):
        attributes = _load(path).get("attributes") or []
        linked = [
            attribute
            for attribute in attributes
            if WORKFLOW_ID in (attribute.get("needed_for_workflows") or [])
            and not attribute_applies_to_all_workflows(attribute, catalog_workflows)
        ]
        if not linked:
            continue

        linked_elements.add(path.stem)
        assert {attribute["name"] for attribute in linked} == set(REQUIREMENTS), path

        by_name = {attribute["name"]: attribute for attribute in linked}
        for name, expected in REQUIREMENTS.items():
            attribute = by_name[name]
            assert attribute["pset"] == expected["pset"], (path, name)
            assert attribute["datatype"] == expected["datatype"], (path, name)
            assert attribute.get("allowed_values") == expected["allowed_values"], (
                path,
                name,
            )
            assert "11" in attribute["needed_in_phases"], (path, name)

    assert linked_elements == TARGET_ELEMENTS


def test_survey_is_activated_by_existing_stock_and_sustainability_goals() -> None:
    existing_goal = _load(REPO_ROOT / "project_goals" / "existing-conditions.yaml")
    existing_levels = {
        level["code"]: set(level["activated_workflows"])
        for level in existing_goal["levels"]
    }
    assert WORKFLOW_ID not in existing_levels["EXIST-01"]
    assert WORKFLOW_ID in existing_levels["EXIST-02"]
    assert WORKFLOW_ID in existing_levels["EXIST-03"]

    sustainability_goal = _load(REPO_ROOT / "project_goals" / "verifiable-sustainability.yaml")
    sustainability_levels = {
        level["code"]: set(level["activated_workflows"])
        for level in sustainability_goal["levels"]
    }
    assert WORKFLOW_ID not in sustainability_levels["SUS-01"]
    assert WORKFLOW_ID not in sustainability_levels["SUS-02"]
    assert WORKFLOW_ID in sustainability_levels["SUS-03"]
