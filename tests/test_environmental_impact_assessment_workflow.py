"""Guard the environmental impact report and its storey-volume element."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/des-environmental-impact-assessment"
GROSS_VOLUME_ATTRIBUTES = {"Name", "PredefinedType", "ObjectType"}


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_environmental_impact_assessment_uses_gross_volume_identity() -> None:
    element = _load("elements/spaces-gross-volume.yaml")
    linked = {
        attribute["name"]
        for attribute in element.get("attributes") or []
        if WORKFLOW_ID in (attribute.get("needed_for_workflows") or [])
    }
    assert linked == GROSS_VOLUME_ATTRIBUTES
