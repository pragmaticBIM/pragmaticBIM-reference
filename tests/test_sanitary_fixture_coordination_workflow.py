"""Guard the architecture-plumbing fixture coordination workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/des-sanitary-fixture-coordination"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attributes(element: str) -> dict[str, dict[str, Any]]:
    data = _load(f"elements/{element}.yaml")
    return {attribute["name"]: attribute for attribute in data["attributes"]}


def test_sanitary_fixture_coordination_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/des-sanitary-fixture-coordination.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "DES-SANITARY-FIXTURE-COORD"
    assert workflow["status"] == "active"
    assert workflow["workflow_group"] == "arbeitsvorbereitung"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/des"
    assert set(workflow["needed_in_domain"]) == {
        "pragmaticbim:domain/architecture",
        "pragmaticbim:domain/mep",
    }
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_sanitary_fixture_coordination_assigns_the_lead_explicitly() -> None:
    description = _load("workflows/des-sanitary-fixture-coordination.yaml")[
        "description"
    ]["de"]

    assert "Architektur stellt Raumlayout und Platzhalter" in description
    assert "Die Sanitärplanung konkretisiert die Objekte" in description
    assert "Typ, genaue Lage, Abmessungen und Anschlüsse" in description
    assert "Vorsatzschalen" in description


def test_fixture_and_plumbing_wall_attributes_link_to_workflow() -> None:
    sanitary_type = _attributes("mep-sanitary-terminal")["PredefinedType"]
    wall_attributes = _attributes("architecture-wall-interior")

    assert "41" in sanitary_type["needed_in_phases"]
    assert WORKFLOW_ID in sanitary_type["needed_for_workflows"]
    for name in ("PredefinedType", "Reference"):
        assert WORKFLOW_ID in wall_attributes[name]["needed_for_workflows"]


def test_fit_out_goal_activates_sanitary_fixture_coordination() -> None:
    goal = _load("project_goals/fit-out-standard.yaml")
    levels = {level["code"]: level for level in goal["levels"]}

    for code in ("FIT-02", "FIT-03"):
        assert WORKFLOW_ID in levels[code]["activated_workflows"]

    elevated = levels["FIT-02"]["description"]
    expected_terms = {
        "de": "Sanitärobjekte",
        "fr": "appareils sanitaires",
        "it": "apparecchi sanitari",
        "en": "sanitary fixtures",
    }
    for lang, term in expected_terms.items():
        assert term in elevated[lang]
