"""Guard the SIA 181 sound insulation workflow, its attributes and rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/des-sound-insulation-sia181"
LANGS = ("de", "fr", "it", "en")
AIRBORNE_ELEMENTS = (
    "architecture-wall-interior",
    "architecture-wall-interior-loadbearing",
    "architecture-slab-floor",
    "architecture-door-interior",
    "architecture-door-exterior",
    "architecture-wall-exterior",
    "architecture-window-exterior",
    "architecture-slab-flat-roof",
)
RULES = (
    "sia-181-001-luftschalldaemmung-anforderung",
    "sia-181-002-trittschallpegel-anforderung",
    "sia-181-003-trennbauteil-mit-anforderung",
    "sia-181-004-raum-laermbelastung-laermempfindlichkeit",
)


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict), relative_path
    return data


def _attributes(element: str) -> dict[str, dict[str, Any]]:
    data = _load(f"elements/{element}.yaml")
    return {attribute["name"]: attribute for attribute in data["attributes"]}


def test_workflow_is_localized_and_activated_by_the_goal() -> None:
    workflow = _load("workflows/des-sound-insulation-sia181.yaml")
    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "DES-SOUND-SIA181"
    assert workflow["status"] == "active"
    assert workflow["countries"] == ["CH"]
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/des"
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)

    goal = _load("project_goals/sound-insulation.yaml")
    for level in goal["levels"]:
        assert WORKFLOW_ID in level["activated_workflows"], level["code"]


def test_spaces_carry_noise_load_and_sensitivity() -> None:
    attributes = _attributes("spaces-interior")
    for name, values in (
        ("NoiseLoad", "noise-load"),
        ("NoiseSensitivity", "noise-sensitivity"),
        ("UsageUnitReference", None),
    ):
        attribute = attributes[name]
        assert WORKFLOW_ID in attribute["needed_for_workflows"], name
        if values:
            assert attribute["pset"] == "ePset_Space", name
            assert attribute["allowed_values"] == f"pragmaticbim:value/{values}", name
            catalogue = _load(f"values/{values}.yaml")["values"]
            lengths = {len(catalogue[lang]) for lang in LANGS}
            assert len(lengths) == 1, values


def test_separating_and_exterior_elements_pair_airborne_target_and_value() -> None:
    for element in AIRBORNE_ELEMENTS:
        attributes = _attributes(element)
        target = attributes["AirborneSoundInsulationMin"]
        delivered = attributes[target["verified_by"]["name"]]
        assert target["performance_property_key"] == (
            "pbs:acoustic_property_airborne_sound_rating_db"
        ), element
        assert target["target_operator"] == "minimum", element
        assert target["pset"].endswith("Requirement"), element
        assert delivered["pset"] == target["verified_by"]["pset"], element
        for attribute in (target, delivered):
            assert WORKFLOW_ID in attribute["needed_for_workflows"], element
            assert all(str(attribute["definition"].get(lang) or "").strip() for lang in LANGS)


def test_rules_are_localized_and_carry_shacl() -> None:
    for slug in RULES:
        rule = _load(f"rules/{slug}.yaml")
        assert rule["id"] == f"pragmaticbim:rule/{slug}"
        assert rule["rule_status"] == "shacl_defined"
        assert rule["domain"] == "pragmaticbim:domain/building-physics"
        assert rule["jurisdiction"] == ["ch"]
        for field in ("name", "description"):
            assert all(str(rule[field].get(lang) or "").strip() for lang in LANGS)
        assert f"rule:{slug} a sh:NodeShape" in rule["shacl"]
        for element in rule["applies_to_elements"]:
            assert (ROOT / "elements" / f"{element.rsplit('/', 1)[-1]}.yaml").is_file(), element
