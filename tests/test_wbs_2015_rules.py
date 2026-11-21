"""WBS 2015 apartment area rules (issue #110)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
RULE_SLUGS = (
    "wbs-2015-001-nettowohnflaeche",
    "wbs-2015-002-zimmergroesse",
)


def _load(slug: str) -> dict[str, Any]:
    path = REPO_ROOT / "rules" / f"{slug}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_wbs_2015_area_rules_are_localized_reviewed() -> None:
    for slug in RULE_SLUGS:
        rule = _load(slug)
        assert rule["id"] == f"pragmaticbim:rule/{slug}"
        assert rule["rule_status"] == "reviewed"
        assert rule["reviewed_by"] in (None, "")
        assert rule["rule_source"]["regulation"] == "pragmaticbim:regulation/wbs-2015"
        assert "K1" in (rule["rule_source"].get("source_quote") or "")
        for field in ("name", "description"):
            block = rule[field]
            for lang in LANGS:
                assert str(block.get(lang) or "").strip(), f"{slug}.{field}.{lang}"


def test_wbs_2015_area_rules_support_furnishability_workflows() -> None:
    furnish = yaml.safe_load(
        (REPO_ROOT / "workflows" / "qas-furnishability-verification.yaml").read_text(encoding="utf-8")
    )
    furniture = yaml.safe_load(
        (REPO_ROOT / "workflows" / "des-furniture-planning.yaml").read_text(encoding="utf-8")
    )
    blob = f"{furnish.get('comment') or ''}\n{furniture.get('comment') or ''}"
    assert "WBS-2015-001" in blob or "wbs-2015-001" in blob.lower() or "WBS 2015" in blob
