"""Guard client-led CDE procurement and continuity requirements."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/bes-owner-cde-procurement"
LANGUAGES = {"de", "fr", "it", "en"}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_owner_cde_workflow_metadata_and_translations() -> None:
    workflow = _load_yaml(
        REPO_ROOT / "workflows" / "bes-owner-cde-procurement.yaml"
    )

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "BES-OWNER-CDE"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/bes"
    assert workflow["workflow_group"] == "grundlagen-bestand"
    assert set(workflow["name"]) == LANGUAGES
    assert set(workflow["description"]) == LANGUAGES
    assert all(str(workflow["name"][lang]).strip() for lang in LANGUAGES)
    assert all(str(workflow["description"][lang]).strip() for lang in LANGUAGES)


def test_owner_cde_workflow_covers_continuity_and_exit() -> None:
    workflow = _load_yaml(
        REPO_ROOT / "workflows" / "bes-owner-cde-procurement.yaml"
    )
    german = str(workflow["description"]["de"])

    for term in ("Bauherrschaft", "Konkurs", "Streit", "Export", "Gesamtleitung"):
        assert term in german


def test_owner_cde_belongs_to_procurement_strategy() -> None:
    procurement = _load_yaml(REPO_ROOT / "project_goals" / "procurement-strategy.yaml")
    planning = _load_yaml(REPO_ROOT / "project_goals" / "planning-certainty.yaml")

    assert procurement["group"] == "rahmenbedingungen"
    for level in procurement["levels"]:
        assert WORKFLOW_ID in level["activated_workflows"]
    for level in planning["levels"]:
        assert WORKFLOW_ID not in (level.get("activated_workflows") or [])
