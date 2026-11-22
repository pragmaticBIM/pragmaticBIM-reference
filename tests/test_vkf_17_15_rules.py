"""VKF 17-15 escape-route signs, safety lighting and safety power: localized, cited, unreviewed (#89)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
REGULATION_ID = "pragmaticbim:regulation/vkf-17-15-2015"


def _rules() -> list[tuple[Path, dict]]:
    return [
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted((REPO_ROOT / "rules").glob("vkf-17-15-*.yaml"))
    ]


def test_regulation_is_localized_swiss_2015() -> None:
    regulation = yaml.safe_load((REPO_ROOT / "regulations" / "vkf-17-15-2015.yaml").read_text(encoding="utf-8"))
    assert regulation["id"] == REGULATION_ID
    assert regulation["edition"] == "2015"
    assert regulation["jurisdiction"] == ["CH"]
    assert regulation["access"] == "free"
    for lang in LANGS:
        assert str(regulation["name"].get(lang) or "").strip(), lang


def test_rules_cover_signs_lighting_and_power() -> None:
    quotes = " ".join(rule["rule_source"]["source_quote"] for _, rule in _rules())
    for clause in ("2.2.1", "2.2.2", "2.2.3", "2.2.4", "3.1.2", "3.1.5", "3.2.2", "3.2.3", "3.2.4", "3.3.2", "3.3.3", "3.3.4", "4.1"):
        assert f"Ziff. {clause}" in quotes, clause


SHACL_RULES = {
    "vkf-17-15-009-sicherheitsbeleuchtung-dauer-schaltung.yaml",
    "vkf-17-15-010-sicherheitsleuchten-anordnung.yaml",
    "vkf-17-15-011-sicherheitsbeleuchtung-beleuchtungsstaerke.yaml",
}


def test_rules_are_localized_cited_and_unreviewed() -> None:
    rules = _rules()
    assert len(rules) >= 15
    for path, rule in rules:
        assert rule["rule_source"]["regulation"] == REGULATION_ID, path
        assert rule["rule_source"]["source_quote"].startswith("VKF 17-15, Ziff. "), path
        expected = "shacl_defined" if path.name in SHACL_RULES else "reviewed"
        assert rule["rule_status"] == expected, path
        assert rule["reviewed_by"] in (None, ""), path
        assert rule["reviewed_at"] in (None, ""), path
        assert rule["jurisdiction"] == ["ch"], path
        assert rule["edition"] == "2015", path
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


def test_rules_apply_to_existing_elements() -> None:
    elements = {p.stem for p in (REPO_ROOT / "elements").glob("*.yaml")}
    for path, rule in _rules():
        for ref in rule["applies_to_elements"]:
            assert ref.removeprefix("pragmaticbim:element/") in elements, f"{path}: {ref}"
