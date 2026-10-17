"""Guard the room-QR defect-management workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/con-defect-management"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_defect_management_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/con-defect-management.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "CON-DEFECT-MGMT"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/con"
    assert workflow["needed_in_domain"] == ["pragmaticbim:domain/architecture"]
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_workflow_defines_the_room_qr_process() -> None:
    description = _load("workflows/con-defect-management.yaml")["description"]["de"]

    for expected in (
        "A4-Kennzeichnung",
        "Raumnummer",
        "Raumnutzung",
        "QR-Code",
        "Mängelmanagement",
        "vorbelegten Formular",
        "Klebeband",
        "Tür oder Fenster",
        "synchronisieren",
        "Abschluss",
    ):
        assert expected in description


def test_room_number_and_use_are_linked_to_workflow() -> None:
    space = _load("elements/spaces-interior.yaml")
    attributes = {attribute["name"]: attribute for attribute in space["attributes"]}

    for name in ("Name", "LongName"):
        assert WORKFLOW_ID in attributes[name]["needed_for_workflows"]
