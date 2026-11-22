"""VKF 25-15 Lufttechnische Anlagen (fire dampers, ducts, plant rooms): localized, cited, unreviewed (#132)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REGULATION_ID = "pragmaticbim:regulation/vkf-25-15-2015"


def _rules() -> list[tuple[Path, dict]]:
    return [
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted((REPO_ROOT / "rules").glob("vkf-25-15-*.yaml"))
    ]


def test_regulation_is_localized_swiss_2015() -> None:
    regulation = yaml.safe_load((REPO_ROOT / "regulations" / "vkf-25-15-2015.yaml").read_text(encoding="utf-8"))
    assert regulation["id"] == REGULATION_ID
    assert regulation["edition"] == "2015"
    assert regulation["jurisdiction"] == ["CH"]
    assert regulation["access"] == "free"
    assert regulation["publisher"] == "VKF"
    for lang in LANGS:
        assert str(regulation["name"].get(lang) or "").strip(), lang


def test_rules_cover_fire_damper_and_duct_clauses() -> None:
    quotes = " ".join(rule["rule_source"]["source_quote"] for _, rule in _rules())
    for clause in (
        "3.1",
        "3.2",
        "3.3",
        "3.4",
        "3.5",
        "3.6",
        "3.7.1",
        "3.7.2",
        "3.7.3",
        "3.7.4",
        "3.7.6",
        "3.7.8",
        "3.8.1",
        "3.8.2",
        "3.10",
        "4.1.1",
        "4.1.2",
        "4.2.1",
        "4.3.1",
        "4.3.2",
        "4.3.3",
        "4.3.4",
    ):
        assert f"Ziff. {clause}" in quotes or f" {clause} " in quotes or f" {clause}," in quotes, clause


def test_rules_are_localized_cited_and_unreviewed() -> None:
    rules = _rules()
    assert len(rules) >= 15
    for path, rule in rules:
        assert rule["rule_source"]["regulation"] == REGULATION_ID, path
        assert rule["rule_source"]["source_quote"].startswith("VKF 25-15, Ziff. "), path
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


def test_fire_damper_rules_apply_to_the_damper_element() -> None:
    by_code = {rule["code"]: rule for _, rule in _rules()}
    for code in ("VKF-25-15-011", "VKF-25-15-012", "VKF-25-15-013"):
        assert "pragmaticbim:element/mep-damper" in by_code[code]["applies_to_elements"], code
    assert "pragmaticbim:element/mep-schematic-duct" in by_code["VKF-25-15-012"]["applies_to_elements"]


def test_codes_and_sort_orders_are_unique_across_rules() -> None:
    codes = [rule["code"] for _, rule in _rules()]
    assert len(codes) == len(set(codes))
    others = {
        yaml.safe_load(p.read_text(encoding="utf-8")).get("sort_order")
        for p in (REPO_ROOT / "rules").glob("vkf-*.yaml")
        if not p.name.startswith("vkf-25-15-")
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
