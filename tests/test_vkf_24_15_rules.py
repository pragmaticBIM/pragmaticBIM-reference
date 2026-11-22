"""VKF 24-15 Wärmetechnische Anlagen (boiler rooms and heat-generating plant): localized, cited, unreviewed (#136)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REGULATION_ID = "pragmaticbim:regulation/vkf-24-15-2015"
PREFIX = "vkf-24-15-"


def _rules() -> list[tuple[Path, dict]]:
    return [
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted((REPO_ROOT / "rules").glob(PREFIX + "*.yaml"))
    ]


def test_regulation_is_localized_swiss_2015() -> None:
    regulation = yaml.safe_load((REPO_ROOT / "regulations" / "vkf-24-15-2015.yaml").read_text(encoding="utf-8"))
    assert regulation["id"] == REGULATION_ID
    assert regulation["edition"] == "2015"
    assert regulation["jurisdiction"] == ["CH"]
    assert regulation["access"] == "free"
    assert regulation["publisher"] == "VKF"
    for lang in LANGS:
        assert str(regulation["name"].get(lang) or "").strip(), lang


def test_rules_cover_the_checkable_clauses() -> None:
    quotes = " ".join(rule["rule_source"]["source_quote"] for _, rule in _rules())
    for clause in ['2.1', '2.2', '2.3', '3.2', '3.3', '3.4', '3.5', '3.6', '3.8', '3.11', '4.1', '4.6', '5.1', '5.5.1', '5.6', '5.8.1', '5.9.1', '6.1', '6.4', '7']:
        assert f"Ziff. {clause}" in quotes or f" {clause} " in quotes or f" {clause}," in quotes or f"{clause}–" in quotes or f"–{clause}" in quotes or quotes.endswith(f" {clause}"), clause


def test_rules_are_localized_cited_and_unreviewed() -> None:
    rules = _rules()
    assert len(rules) >= 18
    for path, rule in rules:
        assert rule["rule_source"]["regulation"] == REGULATION_ID, path
        assert rule["rule_source"]["source_quote"].startswith("VKF 24-15, Ziff. "), path
        assert rule["rule_source"]["source_page"], path
        assert rule["rule_status"] == "reviewed", path
        assert rule["reviewed_by"] in (None, ""), path
        assert rule["reviewed_at"] in (None, ""), path
        assert rule["jurisdiction"] == ["ch"], path
        assert rule["edition"] == "2015", path
        assert str(rule["valid_from"]) == "2015-01-01", path
        assert rule["domain"] == "pragmaticbim:domain/fire-protection", path
        assert rule["id"] == "pragmaticbim:rule/" + path.stem, path
        assert rule["code"] == path.stem[:13].upper(), path
        for field in ("name", "description"):
            for lang in LANGS:
                assert str(rule[field].get(lang) or "").strip(), f"{path}: {field}.{lang}"


def test_rules_do_not_carry_not_checkable_notes() -> None:
    markers = {
        "de": "Noch nicht prüfbar",
        "en": "Not yet checkable",
        "fr": "Pas encore vérifiable",
        "it": "Non ancora verificabile",
    }
    for path, rule in _rules():
        for lang, marker in markers.items():
            assert marker not in " ".join(rule["description"][lang].split()), f"{path}: {lang}"


def test_boiler_room_rules_apply_to_the_boiler_element() -> None:
    by_code = {rule["code"]: rule for _, rule in _rules()}
    for code in ("VKF-24-15-004", "VKF-24-15-005", "VKF-24-15-010"):
        assert "pragmaticbim:element/mep-boiler" in by_code[code]["applies_to_elements"], code
    assert "70 kW" in by_code["VKF-24-15-004"]["description"]["en"]
    assert "1,200 kW" in by_code["VKF-24-15-005"]["description"]["en"]


def test_codes_and_sort_orders_are_unique_across_rules() -> None:
    codes = [rule["code"] for _, rule in _rules()]
    assert len(codes) == len(set(codes))
    others = {
        yaml.safe_load(p.read_text(encoding="utf-8")).get("sort_order")
        for p in (REPO_ROOT / "rules").glob("*.yaml")
        if not p.name.startswith(PREFIX)
    }
    seen: set[int] = set()
    for _, rule in _rules():
        assert rule["sort_order"] not in others, rule["code"]
        assert rule["sort_order"] not in seen, rule["code"]
        seen.add(rule["sort_order"])


def test_rules_apply_to_existing_elements() -> None:
    elements = {p.stem for p in (REPO_ROOT / "elements").glob("*.yaml")}
    for path, rule in _rules():
        assert rule["applies_to_elements"], path
        for ref in rule["applies_to_elements"]:
            assert ref.removeprefix("pragmaticbim:element/") in elements, f"{path}: {ref}"
