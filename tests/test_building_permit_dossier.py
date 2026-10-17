"""Guard the building-permit dossier document and workflow integration."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = {"de", "fr", "it", "en"}


def _load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_building_permit_dossier_is_complete_and_localized() -> None:
    document = _load(REPO_ROOT / "documents" / "building-permit-dossier.yaml")
    assert document["id"] == "pragmaticbim:document/building-permit-dossier"
    assert document["status"] == "active"
    assert document["domain"] == "pragmaticbim:domain/architecture"
    assert set(document["name"]) == LANGS
    assert set(document["definition"]) == LANGS
    assert set(document["description"]) == LANGS
    assert document["scheduled_milestones"] == ["33:M"]


def test_building_permit_workflow_delivers_the_dossier() -> None:
    workflow = _load(REPO_ROOT / "workflows" / "des-building-permit.yaml")
    assert "building-permit dossier" in workflow["comment"]
    for language in LANGS:
        assert "dossier" in workflow["description"][language].lower()
