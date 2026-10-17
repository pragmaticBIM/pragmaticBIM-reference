"""Guard outlet user approval and lighting design coordination."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTLET_WORKFLOW_ID = "pragmaticbim:workflow/qas-outlet-user-approval"
LIGHTING_WORKFLOW_ID = "pragmaticbim:workflow/des-lighting-design-coordination"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attributes(element: str) -> dict[str, dict[str, Any]]:
    data = _load(f"elements/{element}.yaml")
    return {attribute["name"]: attribute for attribute in data["attributes"]}


def test_electrical_coordination_workflows_are_localized_and_active() -> None:
    cases = (
        (
            "workflows/qas-outlet-user-approval.yaml",
            OUTLET_WORKFLOW_ID,
            "QAS-OUTLET-USER",
            "pragmaticbim:workflow/qas",
            "koordination",
        ),
        (
            "workflows/des-lighting-design-coordination.yaml",
            LIGHTING_WORKFLOW_ID,
            "DES-LIGHTING-COORD",
            "pragmaticbim:workflow/des",
            "arbeitsvorbereitung",
        ),
    )

    for path, workflow_id, code, parent, group in cases:
        workflow = _load(path)
        assert workflow["id"] == workflow_id
        assert workflow["code"] == code
        assert workflow["status"] == "active"
        assert workflow["parent_workflow"] == parent
        assert workflow["workflow_group"] == group
        assert set(workflow["needed_in_domain"]) == {
            "pragmaticbim:domain/architecture",
            "pragmaticbim:domain/mep",
        }
        for field in ("name", "description"):
            assert all(
                str(workflow[field].get(lang) or "").strip() for lang in LANGS
            )


def test_outlet_approval_is_type_based_instead_of_occurrence_based() -> None:
    description = _load("workflows/qas-outlet-user-approval.yaml")[
        "description"
    ]["de"]

    assert "ohne jede einzelne Steckdose freigeben zu lassen" in description
    assert "Typenkatalog" in description
    assert "Skizzen oder Modellausschnitte" in description
    assert "Sonderfälle" in description


def test_lighting_workflow_has_explicit_handover_and_approval() -> None:
    description = _load("workflows/des-lighting-design-coordination.yaml")[
        "description"
    ]["de"]

    assert "als Skizze, Plan oder Modell" in description
    assert "Elektro- oder Lichtplanung überführt das Konzept" in description
    assert "geben den koordinierten Stand gemeinsam frei" in description


def test_electrical_elements_link_to_the_new_workflows() -> None:
    outlet_type = _attributes("mep-outlet")["PredefinedType"]
    light_type = _attributes("mep-light-fixture")["PredefinedType"]
    room_use = _attributes("spaces-interior")["LongName"]
    ceiling_type = _attributes("architecture-ceiling-suspended")[
        "PredefinedType"
    ]

    assert "31" in outlet_type["needed_in_phases"]
    assert OUTLET_WORKFLOW_ID in outlet_type["needed_for_workflows"]
    assert OUTLET_WORKFLOW_ID in room_use["needed_for_workflows"]

    assert "31" in light_type["needed_in_phases"]
    assert LIGHTING_WORKFLOW_ID in light_type["needed_for_workflows"]
    assert LIGHTING_WORKFLOW_ID in ceiling_type["needed_for_workflows"]


def test_fit_out_goal_activates_both_electrical_workflows() -> None:
    goal = _load("project_goals/fit-out-standard.yaml")
    levels = {level["code"]: level for level in goal["levels"]}

    for code in ("FIT-02", "FIT-03"):
        activated = levels[code]["activated_workflows"]
        assert OUTLET_WORKFLOW_ID in activated
        assert LIGHTING_WORKFLOW_ID in activated

    elevated = levels["FIT-02"]["description"]
    expected_terms = {
        "de": ("Steckdosen", "Leuchten"),
        "fr": ("prises", "éclairage"),
        "it": ("prese", "illuminotecnica"),
        "en": ("outlet", "lighting"),
    }
    for lang, terms in expected_terms.items():
        assert all(term in elevated[lang] for term in terms)
