"""Regulations catalogue integrity and rule links."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REQUIRED_FIELDS = (
    "id",
    "code",
    "edition",
    "name",
    "publisher",
    "jurisdiction",
    "valid_from",
    "access",
    "url",
)
EXPECTED_IDS = {
    "pragmaticbim:regulation/vkf-15-15-2015",
    "pragmaticbim:regulation/vkf-16-15-2015",
    "pragmaticbim:regulation/sia-181-2020",
    "pragmaticbim:regulation/sia-500-2009",
    "pragmaticbim:regulation/sia-416-2003",
    "pragmaticbim:regulation/wbs-2015",
    "pragmaticbim:regulation/ifc-2x3-tc1",
    "pragmaticbim:regulation/ifc-4-add2-tc1",
    "pragmaticbim:regulation/ifc-4x3-add2",
}


def _load_dir(folder: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / folder).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        if not str(data.get("id") or "").startswith("pragmaticbim:regulation/"):
            continue
        data["_path"] = path
        items.append(data)
    return items


def test_regulations_catalogue_is_complete_and_localized() -> None:
    regulations = _load_dir("regulations")
    by_id = {item["id"]: item for item in regulations}
    assert set(by_id) == EXPECTED_IDS

    for item in regulations:
        path = item["_path"]
        for field in REQUIRED_FIELDS:
            assert field in item, f"{path}: missing {field}"
        assert item["id"].startswith("pragmaticbim:regulation/"), path
        assert item["access"] in {"free", "licensed"}, path
        assert isinstance(item["jurisdiction"], list), path
        name = item["name"]
        assert isinstance(name, dict), path
        for lang in LANGS:
            assert str(name.get(lang) or "").strip(), f"{path}: missing name.{lang}"


def test_superseded_by_and_rule_regulations_resolve() -> None:
    regulations = _load_dir("regulations")
    ids = {item["id"] for item in regulations}

    for item in regulations:
        superseded = item.get("superseded_by")
        if superseded:
            assert superseded in ids, f"{item['_path']}: unknown superseded_by {superseded}"

    for path in sorted((REPO_ROOT / "rules").glob("*.yaml")):
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(rule, dict), path
        source = rule.get("rule_source") or {}
        regulation = source.get("regulation")
        if regulation is None:
            continue
        assert regulation in ids, f"{path}: unknown rule_source.regulation {regulation}"


def test_vkf_and_sia181_rules_link_their_regulation() -> None:
    expected = {
        "vkf-15-15": "pragmaticbim:regulation/vkf-15-15-2015",
        "vkf-16-15": "pragmaticbim:regulation/vkf-16-15-2015",
        "sia-181": "pragmaticbim:regulation/sia-181-2020",
    }
    for path in sorted((REPO_ROOT / "rules").glob("*.yaml")):
        stem = path.stem
        regulation_id = next(
            (rid for prefix, rid in expected.items() if stem.startswith(prefix)),
            None,
        )
        if regulation_id is None:
            continue
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert rule["rule_source"]["regulation"] == regulation_id, path
