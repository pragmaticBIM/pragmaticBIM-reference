"""Fixture spacing matrix (#53)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "rules" / "fixture_spacing.yaml"
SCHEMA = ROOT / "schema" / "fixture-spacing.schema.json"


def _load_matrix() -> dict:
    data = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_fixture_spacing_matches_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(_load_matrix()), key=lambda e: list(e.path))
    assert not errors, errors[0].message


def test_fixture_spacing_pairs_have_sources() -> None:
    pairs = _load_matrix()["pairs"]
    assert len(pairs) >= 7
    for pair in pairs:
        source = pair["source"]
        assert source["kind"] in {"norm", "owner", "project", "default"}
        if source["kind"] == "norm":
            assert source.get("reference")


def test_urinal_urinal_axis_spacing_in_matrix() -> None:
    pairs = _load_matrix()["pairs"]
    match = [
        p
        for p in pairs
        if p["between"] == ["urinal", "urinal"] and p["measure"] == "axis"
    ]
    assert len(match) == 1
    assert match[0]["distance"]["min"] == 0.7


def test_urinal_component_has_no_axis_spacing_min() -> None:
    urinal = yaml.safe_load(
        (ROOT / "components" / "urinal.yaml").read_text(encoding="utf-8")
    )
    assert "axis_spacing_min" not in (urinal.get("placement") or {})


def test_lookup_helpers_cover_each_pair() -> None:
    from checks import fixture_spacing as fs

    for pair in _load_matrix()["pairs"]:
        a, b = pair["between"]
        found = fs.min_distance(a, b)
        assert found is not None
        assert found.min == pair["distance"]["min"]
        assert found.measure == pair["measure"]
        # Compact bathroom distances: WC–washbasin 0.20 edge
        if set(pair["between"]) == {"toilet", "washbasin"}:
            assert found.min == 0.20
