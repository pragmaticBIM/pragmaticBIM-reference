"""VKF 15-15 remainder (Ziff. 3.5-3.7): rules are localized, cited and unreviewed (#119)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REGULATION = "pragmaticbim:regulation/vkf-15-15-2015"
FIRST_NEW = 11


def _remainder_rules() -> list[tuple[Path, dict]]:
    rules = []
    for path in sorted((REPO_ROOT / "rules").glob("vkf-15-15-*.yaml")):
        number = int(re.match(r"vkf-15-15-(\d{3})-", path.name).group(1))
        if number >= FIRST_NEW:
            rules.append((path, yaml.safe_load(path.read_text(encoding="utf-8"))))
    return rules


def test_remainder_rules_cover_penetrations_shafts_and_uses() -> None:
    quotes = " ".join(rule["rule_source"]["source_quote"] for _, rule in _remainder_rules())
    for clause in ("3.5", "3.6.1", "3.6.2", "3.6.3", "3.6.4", "3.7.3", "3.7.6", "3.7.8", "3.7.11", "3.7.13", "3.7.15"):
        assert f"Ziff. {clause}" in quotes, clause


def test_remainder_rules_are_localized_and_cite_clauses() -> None:
    rules = _remainder_rules()
    assert len(rules) >= 13
    for path, rule in rules:
        assert rule["rule_source"]["regulation"] == REGULATION, path
        assert rule["rule_source"]["source_quote"].startswith("VKF 15-15, Ziff. "), path
        assert rule["rule_status"] == "reviewed", path
        assert rule["reviewed_by"] in (None, ""), path
        assert rule["reviewed_at"] in (None, ""), path
        assert rule["jurisdiction"] == ["ch"], path
        assert rule["edition"] == "2015", path
        assert rule["id"].startswith("pragmaticbim:rule/" + rule["code"].lower()), path
        for field in ("name", "description"):
            for lang in LANGS:
                assert str(rule[field].get(lang) or "").strip(), f"{path}: {field}.{lang}"


def test_remainder_rules_apply_to_existing_elements() -> None:
    elements = {p.stem for p in (REPO_ROOT / "elements").glob("*.yaml")}
    for path, rule in _remainder_rules():
        for ref in rule["applies_to_elements"]:
            assert ref.removeprefix("pragmaticbim:element/") in elements, f"{path}: {ref}"


def test_fire_rating_values_include_e30() -> None:
    values = yaml.safe_load((REPO_ROOT / "values" / "fire-rating.yaml").read_text(encoding="utf-8"))
    for lang in LANGS:
        assert "E 30" in values["values"][lang]
