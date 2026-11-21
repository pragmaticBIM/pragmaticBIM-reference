"""Rules use lowercase ISO jurisdiction codes (#69 part 1)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")


def test_catalogue_rules_use_lowercase_jurisdiction() -> None:
    for path in sorted((REPO / "rules").glob("*.yaml")):
        if path.name == "fixture_spacing.yaml":
            continue
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        jurisdictions = rule.get("jurisdiction") or []
        assert jurisdictions, path
        for code in jurisdictions:
            assert code == code.lower(), f"{path}: jurisdiction {code!r} must be lowercase"


def test_vkf_rules_carry_edition_and_valid_from() -> None:
    for path in sorted((REPO / "rules").glob("vkf-*.yaml")):
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert rule.get("edition") == "2015", path
        assert rule.get("valid_from") == "2015-01-01", path
