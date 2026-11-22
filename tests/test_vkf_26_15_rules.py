"""VKF 26-15 Gefährliche Stoffe (storage and handling of hazardous substances): localized, cited, unreviewed (#137)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REGULATION_ID = "pragmaticbim:regulation/vkf-26-15-2015"
PREFIX = "vkf-26-15-"


def _rules() -> list[tuple[Path, dict]]:
    return [
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted((REPO_ROOT / "rules").glob(PREFIX + "*.yaml"))
    ]


def test_regulation_is_localized_swiss_2015() -> None:
    regulation = yaml.safe_load((REPO_ROOT / "regulations" / "vkf-26-15-2015.yaml").read_text(encoding="utf-8"))
    assert regulation["id"] == REGULATION_ID
    assert regulation["edition"] == "2015"
    assert regulation["jurisdiction"] == ["CH"]
    assert regulation["access"] == "free"
    assert regulation["publisher"] == "VKF"
    for lang in LANGS:
        assert str(regulation["name"].get(lang) or "").strip(), lang


def test_rules_cover_the_checkable_clauses() -> None:
    quotes = " ".join(rule["rule_source"]["source_quote"] for _, rule in _rules())
    for clause in ['3.1', '3.2', '3.3', '3.4', '3.5.1', '3.5.3', '3.5.4', '3.6.1', '4.1', '4.2', '4.3', '4.6', '5.1', '5.2.1', '5.2.2', '5.2.3', '5.2.4', '5.4', '6', '7', '8.1', '8.2', '8.3', '9', '10.1', '10.2', '11.1.3', '11.2.1', '11.2.2', '11.2.6', '11.3.1', '11.3.2', '11.3.3', '11.4']:
        assert f"Ziff. {clause}" in quotes or f" {clause} " in quotes or f" {clause}," in quotes or f"{clause}–" in quotes or f"–{clause}" in quotes or quotes.endswith(f" {clause}"), clause


def test_rules_are_localized_cited_and_unreviewed() -> None:
    rules = _rules()
    assert len(rules) >= 28
    for path, rule in rules:
        assert rule["rule_source"]["regulation"] == REGULATION_ID, path
        assert rule["rule_source"]["source_quote"].startswith("VKF 26-15, Ziff. "), path
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


def test_storage_quantity_and_lightning_thresholds_are_stated() -> None:
    by_code = {rule["code"]: rule for _, rule in _rules()}
    assert "600 t" in by_code["VKF-26-15-003"]["description"]["en"]
    assert "2,000 l" in by_code["VKF-26-15-006"]["description"]["en"]
    assert "1,000 kg" in by_code["VKF-26-15-006"]["description"]["en"]
    assert "pragmaticbim:element/mep-tank" in by_code["VKF-26-15-006"]["applies_to_elements"]


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
