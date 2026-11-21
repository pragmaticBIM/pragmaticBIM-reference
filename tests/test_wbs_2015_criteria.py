"""WBS 2015 criteria inventory (issue #73, part 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY = REPO_ROOT / "regulations" / "wbs-2015-criteria.yaml"
LANGS = ("de", "fr", "it", "en")
CHECKABILITY = frozenset({"model_checkable", "partly_checkable", "assessment_only"})
EXPECTED_IDS = {f"K{n}" for n in range(1, 26)}
AREAS = frozenset({"wohnstandort", "wohnanlage", "wohnung"})


def _load() -> dict[str, Any]:
    data = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_wbs_2015_criteria_inventory() -> None:
    data = _load()
    assert data["regulation"] == "pragmaticbim:regulation/wbs-2015"
    assert data["edition"] == "2015"
    assert set(data["checkability_values"]) == CHECKABILITY

    criteria = data["criteria"]
    assert len(criteria) == 25
    ids = {item["id"] for item in criteria}
    assert ids == EXPECTED_IDS

    for item in criteria:
        assert item["area"] in AREAS, item["id"]
        assert item["checkability"] in CHECKABILITY, item["id"]
        measures = item["measures"]
        assert isinstance(measures, dict)
        for lang in LANGS:
            assert str(measures.get(lang) or "").strip(), f"{item['id']} missing measures.{lang}"
        assert str(item.get("code") or "").strip(), item["id"]

    assessment = sum(1 for item in criteria if item["checkability"] == "assessment_only")
    assert assessment == 6, "K1–K6 should be assessment-only (location context)"
    assert any(item["checkability"] == "model_checkable" for item in criteria)