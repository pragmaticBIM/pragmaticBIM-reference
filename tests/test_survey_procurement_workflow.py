"""Guard the staged procurement scopes for existing-condition foundations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/bes-survey-existing-model-procurement"
POINT_CLOUD_WORKFLOW_ID = (
    "pragmaticbim:workflow/bes-existing-building-point-cloud-procurement"
)
STRUCTURE_WORKFLOW_ID = (
    "pragmaticbim:workflow/bes-existing-structure-model-procurement"
)
BUILDING_MEP_WORKFLOW_ID = (
    "pragmaticbim:workflow/bes-existing-building-mep-model-procurement"
)
LANGUAGES = ("de", "fr", "it", "en")
EXPECTED_DOMAINS = {
    "pragmaticbim:domain/surveyor",
    "pragmaticbim:domain/architecture",
    "pragmaticbim:domain/structural",
    "pragmaticbim:domain/mep",
    "pragmaticbim:domain/infrastructure",
}


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_survey_procurement_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/bes-survey-existing-model-procurement.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "BES-EXISTING-SITE"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/bes"
    assert workflow["countries"] == ["CH"]
    assert set(workflow["needed_in_domain"]) == EXPECTED_DOMAINS
    for field in ("name", "description"):
        assert set(workflow[field]) == set(LANGUAGES)
        assert all(str(workflow[field][language]).strip() for language in LANGUAGES)


def test_building_point_cloud_workflow_is_localized_and_active() -> None:
    workflow = _load(
        "workflows/bes-existing-building-point-cloud-procurement.yaml"
    )

    assert workflow["id"] == POINT_CLOUD_WORKFLOW_ID
    assert workflow["code"] == "BES-EXISTING-POINT-CLOUD"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/bes"
    assert workflow["countries"] == ["CH"]
    for field in ("name", "description"):
        assert set(workflow[field]) == set(LANGUAGES)
        assert all(str(workflow[field][language]).strip() for language in LANGUAGES)


def test_survey_procurement_is_activated_for_every_existing_stock_level() -> None:
    goal = _load("project_goals/existing-conditions.yaml")

    levels = {
        level["code"]: set(level["activated_workflows"]) for level in goal["levels"]
    }

    assert WORKFLOW_ID in levels["EXIST-01"]
    assert POINT_CLOUD_WORKFLOW_ID not in levels["EXIST-01"]
    assert STRUCTURE_WORKFLOW_ID not in levels["EXIST-01"]
    assert BUILDING_MEP_WORKFLOW_ID not in levels["EXIST-01"]

    assert {
        WORKFLOW_ID,
        POINT_CLOUD_WORKFLOW_ID,
        STRUCTURE_WORKFLOW_ID,
    } <= levels["EXIST-02"]
    assert BUILDING_MEP_WORKFLOW_ID not in levels["EXIST-02"]

    assert {
        WORKFLOW_ID,
        POINT_CLOUD_WORKFLOW_ID,
        STRUCTURE_WORKFLOW_ID,
        BUILDING_MEP_WORKFLOW_ID,
    } <= levels["EXIST-03"]


def test_building_mep_scope_includes_structure_and_additional_elements() -> None:
    additional_elements = {
        "architecture-built-in-furniture.yaml",
        "spaces-interior.yaml",
        "spaces-exterior.yaml",
        "spaces-luftraum.yaml",
    }
    mapped_additional_elements: set[str] = set()

    for path in (ROOT / "elements").glob("*.yaml"):
        element = _load(str(path.relative_to(ROOT)))
        for attribute in element.get("attributes", []):
            workflows = set(attribute.get("needed_for_workflows") or [])
            if STRUCTURE_WORKFLOW_ID in workflows:
                assert BUILDING_MEP_WORKFLOW_ID in workflows
            if BUILDING_MEP_WORKFLOW_ID in workflows and path.name in additional_elements:
                mapped_additional_elements.add(path.name)

    assert mapped_additional_elements == additional_elements

    gross_volume = _load("elements/spaces-gross-volume.yaml")
    gross_volume_workflows = {
        workflow
        for attribute in gross_volume["attributes"]
        for workflow in attribute.get("needed_for_workflows") or []
    }
    assert {
        STRUCTURE_WORKFLOW_ID,
        BUILDING_MEP_WORKFLOW_ID,
    } <= gross_volume_workflows
