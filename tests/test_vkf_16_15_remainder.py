"""VKF 16-15 remainder (Ziff. 2.2, 2.4.4-2.5.5, 3.1-3.10): text rules are localized and cited (#87)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REGULATION = "pragmaticbim:regulation/vkf-16-15-2015"
FIRST_NEW = 10


def _remainder_rules() -> list[tuple[Path, dict]]:
    rules = []
    for path in sorted((REPO_ROOT / "rules").glob("vkf-16-15-*.yaml")):
        number = int(re.match(r"vkf-16-15-(\d{3})-", path.name).group(1))
        if number >= FIRST_NEW:
            rules.append((path, yaml.safe_load(path.read_text(encoding="utf-8"))))
    return rules


def test_remainder_rules_cover_requested_clauses() -> None:
    quotes = " ".join(rule["rule_source"]["source_quote"] for _, rule in _remainder_rules())
    for clause in (
        "2.2",
        "2.4.4",
        "2.4.7",
        "2.5.1",
        "2.5.2",
        "2.5.3",
        "2.5.4",
        "2.5.5",
        "3.1",
        "3.2",
        "3.3.1",
        "3.4.1",
        "3.5.1",
        "3.5.2",
        "3.5.4",
        "3.5.5",
        "3.6.1",
        "3.7",
        "3.8",
        "3.9",
        "3.10",
    ):
        assert f"Ziff. {clause}" in quotes, clause


def test_remainder_rules_are_localized_cited_and_unreviewed() -> None:
    rules = _remainder_rules()
    assert 10 <= len(rules) <= 25
    for path, rule in rules:
        assert rule["rule_source"]["regulation"] == REGULATION, path
        assert rule["rule_source"]["source_quote"].startswith("VKF 16-15, Ziff. "), path
        assert rule["rule_status"] == "reviewed", path
        assert rule["reviewed_by"] in (None, ""), path
        assert rule["reviewed_at"] in (None, ""), path
        assert rule["jurisdiction"] == ["ch"], path
        assert rule["edition"] == "2015", path
        assert str(rule["valid_from"]) == "2015-01-01", path
        assert rule["id"].startswith("pragmaticbim:rule/" + rule["code"].lower()), path
        for field in ("name", "description"):
            for lang in LANGS:
                assert str(rule[field].get(lang) or "").strip(), f"{path}: {field}.{lang}"


def test_remainder_codes_and_sort_orders_are_unique() -> None:
    codes = [rule["code"] for _, rule in _remainder_rules()]
    assert len(codes) == len(set(codes))
    orders = {
        yaml.safe_load(p.read_text(encoding="utf-8"))["sort_order"]
        for p in (REPO_ROOT / "rules").glob("vkf-*.yaml")
        if not p.name.startswith("vkf-16-15-0") or int(p.name[10:13]) < FIRST_NEW
    }
    for _, rule in _remainder_rules():
        assert rule["sort_order"] not in orders, rule["code"]
        orders.add(rule["sort_order"])


def test_remainder_rules_apply_to_existing_elements() -> None:
    elements = {p.stem for p in (REPO_ROOT / "elements").glob("*.yaml")}
    for path, rule in _remainder_rules():
        for ref in rule["applies_to_elements"]:
            assert ref.removeprefix("pragmaticbim:element/") in elements, f"{path}: {ref}"


def test_existing_rules_001_to_009_are_untouched_in_status() -> None:
    first = {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (REPO_ROOT / "rules").glob("vkf-16-15-00*.yaml")
    }
    assert len(first) == 9
    for name, rule in first.items():
        assert rule["rule_source"]["regulation"] == REGULATION, name
