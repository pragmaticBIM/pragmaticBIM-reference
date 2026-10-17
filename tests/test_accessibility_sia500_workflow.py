"""Guard the SIA 500 accessibility verification workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/qas-accessibility-sia500-verification"
ELEMENT_ID = "pragmaticbim:element/architecture-movement-clearance"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attributes(element: str) -> dict[str, dict[str, Any]]:
    data = _load(f"elements/{element}.yaml")
    return {attribute["name"]: attribute for attribute in data["attributes"]}


def test_accessibility_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/qas-accessibility-sia500-verification.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "QAS-ACCESS-SIA500"
    assert workflow["status"] == "active"
    assert workflow["countries"] == ["CH"]
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/qas"
    assert workflow["workflow_group"] == "fachpruefung"
    assert workflow["needed_in_domain"] == [
        "pragmaticbim:domain/architecture"
    ]
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_accessibility_workflow_states_the_permit_risk_and_proof_layers() -> None:
    description = _load("workflows/qas-accessibility-sia500-verification.yaml")[
        "description"
    ]["de"]

    assert "vor dem Baugesuch sichtbar machen" in description
    assert "Bewegungs- und Manövrierflächen" in description
    assert "Massstab am Plan" in description
    assert "1.40 × 1.70 m" in description
    assert "1.40 × 1.40 m" in description
    assert "vorzugsweise 0.60 m, mindestens aber 0.20 m" in description
    assert "Regelprüfbericht für Türen und Räume" in description
    assert "Kollisionsbericht für die Bewegungsflächen" in description
    assert "Schwellen bis 25 mm" in description


def test_movement_clearance_is_a_typed_proxy_in_architecture_model() -> None:
    element = _load("elements/architecture-movement-clearance.yaml")
    attributes = {attribute["name"]: attribute for attribute in element["attributes"]}
    architecture_model = _load("models/architecture.yaml")

    assert element["id"] == ELEMENT_ID
    assert element["entity_ifc4"] == "IfcBuildingElementProxy"
    assert all(str(element["name"].get(lang) or "").strip() for lang in LANGS)
    assert set(attributes) == {"Name", "PredefinedType", "ObjectType"}
    assert (
        attributes["Name"]["allowed_values"]
        == "pragmaticbim:value/name-movement-clearance"
    )
    assert (
        attributes["ObjectType"]["allowed_values"]
        == "pragmaticbim:value/objecttype-movement-clearance"
    )
    for attribute in attributes.values():
        assert WORKFLOW_ID in attribute["needed_for_workflows"]
    assert ELEMENT_ID in architecture_model["included_elements"]


def test_rooms_and_doors_supply_the_rule_check_data() -> None:
    room_attributes = _attributes("spaces-interior")

    assert WORKFLOW_ID in room_attributes["LongName"]["needed_for_workflows"]
    assert WORKFLOW_ID in room_attributes["NetFloorArea"]["needed_for_workflows"]
    accessible = room_attributes["HandicapAccessible"]
    assert accessible["pset"] == "Pset_SpaceCommon"
    assert accessible["datatype"] == "IfcBoolean"
    assert WORKFLOW_ID in accessible["needed_for_workflows"]

    for door in ("architecture-door-interior", "architecture-door-exterior"):
        door_attributes = _attributes(door)
        assert WORKFLOW_ID in door_attributes["OverallWidth"][
            "needed_for_workflows"
        ]
        assert not any("Threshold" in name for name in door_attributes)


def test_permit_goal_activates_accessibility_verification() -> None:
    goal = _load("project_goals/permit-certainty.yaml")
    levels = {level["code"]: level for level in goal["levels"]}
    medium = levels["BEW-02"]

    assert WORKFLOW_ID in medium["activated_workflows"]
    expected_terms = {
        "de": "SIA 500",
        "fr": "SIA 500",
        "it": "SIA 500",
        "en": "SIA 500",
    }
    for lang, term in expected_terms.items():
        assert term in medium["description"][lang]
