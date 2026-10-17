"""Guard the model-based final-measurement workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/con-final-measurement-from-model"
LANGS = ("de", "fr", "it", "en")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_final_measurement_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/con-final-measurement-from-model.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "CON-FINAL-MEASUREMENT"
    assert workflow["status"] == "active"
    assert workflow["countries"] == ["CH"]
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/con"
    assert set(workflow["needed_in_domain"]) == {
        "pragmaticbim:domain/architecture",
        "pragmaticbim:domain/structural",
        "pragmaticbim:domain/mep",
    }
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_tender_defines_effective_measurement_and_npk_deviations() -> None:
    description = _load("workflows/con-final-measurement-from-model.yaml")[
        "description"
    ]["de"]

    assert "Effektivausmass" in description
    assert "Ausschreibung und Werkvertrag" in description
    assert "Abweichungen von den NPK-Ausmassbestimmungen" in description
    assert "nicht modellierten Leistungen und Bestellungsänderungen" in description
    assert "Cashflow" in description
