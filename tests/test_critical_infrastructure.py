"""Guard critical-infrastructure framework goal and security workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
GOAL_ID = "pragmaticbim:project-goal/critical-infrastructure"
INSERT_WF = "pragmaticbim:workflow/des-critical-area-insert-model"
QAS_WF = "pragmaticbim:workflow/qas-building-security-verification"
LANGUAGES = {"de", "fr", "it", "en"}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_critical_infrastructure_goal_metadata() -> None:
    goal = _load_yaml(REPO_ROOT / "project_goals" / "critical-infrastructure.yaml")

    assert goal["id"] == GOAL_ID
    assert goal["code"] == "PG-12"
    assert goal["group"] == "rahmenbedingungen"
    assert goal["status"] == "active"
    assert set(goal["name"]) == LANGUAGES
    assert set(goal["tag"]) == LANGUAGES
    assert set(goal["description"]) == LANGUAGES


def test_critical_infrastructure_high_activates_security_workflows() -> None:
    goal = _load_yaml(REPO_ROOT / "project_goals" / "critical-infrastructure.yaml")
    levels = {level["id"]: level for level in goal["levels"]}

    low = levels["pragmaticbim:project-goal-level/critical-infrastructure-low"]
    medium = levels["pragmaticbim:project-goal-level/critical-infrastructure-medium"]
    high = levels["pragmaticbim:project-goal-level/critical-infrastructure-high"]

    assert low["activated_workflows"] == []
    assert medium["activated_workflows"] == []
    assert set(high["activated_workflows"]) == {INSERT_WF, QAS_WF}


def test_security_workflows_metadata_and_translations() -> None:
    for slug, code, group, parent in (
        (
            "des-critical-area-insert-model",
            "DES-CRIT-INSERT",
            "fachplanung-koordination",
            "pragmaticbim:workflow/des",
        ),
        (
            "qas-building-security-verification",
            "QAS-BUILD-SEC",
            "fachpruefung",
            "pragmaticbim:workflow/qas",
        ),
    ):
        workflow = _load_yaml(REPO_ROOT / "workflows" / f"{slug}.yaml")
        assert workflow["id"] == f"pragmaticbim:workflow/{slug}"
        assert workflow["code"] == code
        assert workflow["status"] == "active"
        assert workflow["workflow_group"] == group
        assert workflow["parent_workflow"] == parent
        assert set(workflow["name"]) == LANGUAGES
        assert set(workflow["description"]) == LANGUAGES


def test_security_value_catalogues_exist() -> None:
    level = _load_yaml(REPO_ROOT / "values" / "security-level.yaml")
    assert level["id"] == "pragmaticbim:value/security-level"
    assert level["values"]["de"] == [
        "Öffentlich",
        "Intern",
        "Eingeschränkt",
        "Hochgesichert",
    ]
    assert level["values"]["en"] == [
        "Public",
        "Internal",
        "Restricted",
        "High security",
    ]

    goal = _load_yaml(REPO_ROOT / "values" / "security-protection-goal.yaml")
    assert goal["id"] == "pragmaticbim:value/security-protection-goal"
    assert goal["values"]["de"] == [
        "Einbruch",
        "Sabotage",
        "Spionage",
        "Vandalismus",
    ]
    assert goal["values"]["en"] == [
        "Burglary",
        "Sabotage",
        "Espionage",
        "Vandalism",
    ]

    rating = _load_yaml(REPO_ROOT / "values" / "security-rating.yaml")
    assert rating["id"] == "pragmaticbim:value/security-rating"
    assert set(rating["values"]["en"]) == {
        "RC1",
        "RC2",
        "RC3",
        "RC4",
        "RC5",
        "RC6",
    }


def test_space_and_opening_security_attributes() -> None:
    spaces = _load_yaml(REPO_ROOT / "elements" / "spaces-interior.yaml")
    space_attrs = {attr["name"]: attr for attr in spaces["attributes"]}
    for name in ("SecurityZoneReference", "SecurityLevel", "ProtectionGoal"):
        assert name in space_attrs
        assert QAS_WF in space_attrs[name]["needed_for_workflows"]

    assert space_attrs["SecurityLevel"]["allowed_values"] == (
        "pragmaticbim:value/security-level"
    )
    assert space_attrs["ProtectionGoal"]["allowed_values"] == (
        "pragmaticbim:value/security-protection-goal"
    )
    assert INSERT_WF in space_attrs["SecurityZoneReference"]["needed_for_workflows"]

    for element_slug, pset in (
        ("architecture-door-exterior", "Pset_DoorCommon"),
        ("architecture-door-interior", "Pset_DoorCommon"),
        ("architecture-window-exterior", "Pset_WindowCommon"),
    ):
        element = _load_yaml(REPO_ROOT / "elements" / f"{element_slug}.yaml")
        attrs = {attr["name"]: attr for attr in element["attributes"]}
        rating = attrs["SecurityRating"]
        assert rating["pset"] == pset
        assert rating["allowed_values"] == "pragmaticbim:value/security-rating"
        assert QAS_WF in rating["needed_for_workflows"]


def test_building_security_concept_document() -> None:
    doc = _load_yaml(REPO_ROOT / "documents" / "building-security-concept.yaml")
    assert doc["id"] == "pragmaticbim:document/building-security-concept"
    assert doc["code"] == "GSK"
    assert doc["status"] == "active"
    assert set(doc["name"]) == LANGUAGES
    assert set(doc["description"]) == LANGUAGES
