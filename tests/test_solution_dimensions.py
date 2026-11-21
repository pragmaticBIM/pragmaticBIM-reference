"""Guard the solution-box catalog (issue #67)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DIM_DIR = REPO_ROOT / "solution_dimensions"
USES_DIR = REPO_ROOT / "uses"
LANGS = ("de", "fr", "it", "en")
SCOPES = {"project", "site", "building", "unit"}
STEPS = {"form", "access", "grid", "units", "spaces"}

EXPECTED_FILES = {
    "gebaeudeform.yaml",
    "erschliessungstyp.yaml",
    "tragsystem.yaml",
    "schachtstrategie.yaml",
    "bauweise.yaml",
    "ausbauraster.yaml",
    "achsraster.yaml",
    "orientierung.yaml",
    "grundrissorganisation.yaml",
}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _dimensions() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, _load(path)) for path in sorted(DIM_DIR.glob("*.yaml"))]


def _localized(label: str, value: Any) -> None:
    assert isinstance(value, dict), label
    for lang in LANGS:
        text = value.get(lang)
        assert isinstance(text, str) and text.strip(), f"{label}.{lang}"


def test_expected_dimension_files_present() -> None:
    found = {path.name for path in DIM_DIR.glob("*.yaml")}
    assert found == EXPECTED_FILES


def test_dimension_ids_codes_and_sort_orders_are_unique() -> None:
    ids: list[str] = []
    codes: list[str] = []
    sorts: list[int] = []
    option_ids: list[str] = []
    option_codes: list[str] = []
    for path, dim in _dimensions():
        ids.append(dim["id"])
        codes.append(dim["code"])
        sorts.append(dim["sort_order"])
        for option in dim["options"]:
            option_ids.append(option["id"])
            option_codes.append(option["code"])
    assert len(ids) == len(set(ids))
    assert len(codes) == len(set(codes))
    assert len(sorts) == len(set(sorts))
    assert len(option_ids) == len(set(option_ids))
    assert len(option_codes) == len(set(option_codes))


def test_dimension_fields_and_localisation() -> None:
    known_uses = {
        yaml.safe_load(path.read_text(encoding="utf-8"))["id"]
        for path in USES_DIR.glob("*.yaml")
    }
    for path, dim in _dimensions():
        assert dim["id"].startswith("pragmaticbim:solution-dimension/")
        assert dim["status"] == "active"
        assert dim["scope"] in SCOPES, path.name
        assert dim["step"] in STEPS, path.name
        assert isinstance(dim.get("allows_multiple", False), bool)
        _localized(f"{path.name}.name", dim["name"])
        if "description" in dim:
            _localized(f"{path.name}.description", dim["description"])
        for use in dim.get("uses") or []:
            assert use in known_uses, use
        assert dim["options"], path.name
        sorts = [option["sort_order"] for option in dim["options"]]
        assert sorts == sorted(sorts), path.name
        for option in dim["options"]:
            assert option["id"].startswith("pragmaticbim:solution-option/")
            assert option["status"] == "active"
            _localized(f"{option['id']}.name", option["name"])
            if "description" in option:
                _localized(f"{option['id']}.description", option["description"])


def test_exclusive_keine_and_bauweise_has_none() -> None:
    for path, dim in _dimensions():
        exclusive = [o for o in dim["options"] if o.get("exclusive")]
        if path.name == "bauweise.yaml":
            assert exclusive == [], "Bauweise must not offer Keine"
            continue
        assert len(exclusive) == 1, path.name
        assert exclusive[0]["name"]["de"] == "Keine"


def test_excludes_point_at_known_options() -> None:
    known = {
        option["id"]
        for _, dim in _dimensions()
        for option in dim["options"]
    }
    for _, dim in _dimensions():
        for option in dim["options"]:
            for excluded in option.get("excludes") or []:
                assert excluded in known, f"{option['id']} excludes unknown {excluded}"
                assert excluded != option["id"]


def test_parameter_sets_cover_general_and_keys() -> None:
    for _, dim in _dimensions():
        for option in dim["options"]:
            sets = option.get("parameters") or []
            if not sets:
                continue
            jurisdictions = [entry.get("jurisdiction", "general") for entry in sets]
            assert "general" in jurisdictions, option["id"]
            general = next(entry for entry in sets if entry.get("jurisdiction", "general") == "general")
            general_keys = set(general["values"])
            assert general_keys, option["id"]
            for entry in sets:
                for key, param in entry["values"].items():
                    assert key in general_keys, f"{option['id']} key {key} missing from general"
                    assert key[0].islower() and all(c.isalnum() or c == "_" for c in key)
                    assert isinstance(param["value"], (int, float))


def test_issue_67_excludes_and_scopes() -> None:
    by_file = {path.name: dim for path, dim in _dimensions()}

    assert by_file["gebaeudeform.yaml"]["scope"] == "building"
    assert by_file["gebaeudeform.yaml"]["step"] == "form"
    assert by_file["erschliessungstyp.yaml"]["step"] == "access"
    assert by_file["orientierung.yaml"]["scope"] == "unit"
    assert by_file["grundrissorganisation.yaml"]["scope"] == "unit"

    hof = next(
        o for o in by_file["erschliessungstyp.yaml"]["options"]
        if o["id"].endswith("/erschliessung-hof-galerie")
    )
    assert "pragmaticbim:solution-option/gebaeudeform-hofbau" not in (hof.get("excludes") or [])
    assert "pragmaticbim:solution-option/gebaeudeform-riegel" in hof["excludes"]

    ring = next(
        o for o in by_file["erschliessungstyp.yaml"]["options"]
        if o["id"].endswith("/erschliessung-ring-kern")
    )
    assert "pragmaticbim:solution-option/gebaeudeform-punkt" not in (ring.get("excludes") or [])
    assert "pragmaticbim:solution-option/gebaeudeform-hofbau" in ring["excludes"]

    dual = next(
        o for o in by_file["orientierung.yaml"]["options"]
        if o["id"].endswith("/orientierung-durchgesteckt")
    )
    assert dual["excludes"] == ["pragmaticbim:solution-option/erschliessung-mittelgang"]

    wide = next(
        o for o in by_file["achsraster.yaml"]["options"]
        if o["id"].endswith("/achsraster-8-75")
    )
    assert "pragmaticbim:solution-option/tragsystem-schottenbau" in wide["excludes"]
