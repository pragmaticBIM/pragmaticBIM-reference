"""Guard the space-to-wall requirements workflow and its catalogue inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/des-wall-requirements-from-space-use"
FIRE_CONCEPT_ID = "pragmaticbim:workflow/des-fire-protection-concept"
LANGS = ("de", "fr", "it", "en")
PHASES = ["31", "32", "33", "41", "51", "52", "53", "61", "62"]


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attributes(element: str) -> dict[str, dict[str, Any]]:
    data = _load(f"elements/{element}.yaml")
    return {attribute["name"]: attribute for attribute in data["attributes"]}


def test_wall_requirements_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/des-wall-requirements-from-space-use.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "DES-WALL-REQUIREMENTS"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/des"
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_fire_compartment_reference_contract() -> None:
    attribute = _attributes("spaces-interior")["FireCompartmentReference"]

    assert attribute["pset"] == "ePset_Space"
    assert attribute["datatype"] == "IfcIdentifier"
    assert attribute["needed_in_phases"] == PHASES
    assert attribute["ifc_versions"] == ["ifc2x3", "ifc4", "ifc4x3"]
    assert attribute["status"] == "active"
    assert all(
        str(attribute["definition"].get(lang) or "").strip() for lang in LANGS
    )
    assert {WORKFLOW_ID, FIRE_CONCEPT_ID}.issubset(
        attribute["needed_for_workflows"]
    )


def test_wall_requirements_workflow_is_activated_at_high_planning_level() -> None:
    goal = _load("project_goals/planning-certainty.yaml")
    high_level = next(
        level
        for level in goal["levels"]
        if level["id"] == "pragmaticbim:project-goal-level/planning-high"
    )

    assert WORKFLOW_ID in high_level["activated_workflows"]


@pytest.mark.parametrize(
    ("element", "required_attributes"),
    [
        (
            "spaces-interior",
            ("LongName", "UsageUnitReference", "FireCompartmentReference"),
        ),
        (
            "architecture-wall-interior",
            (
                "IsExternal",
                "BelowTerrain",
                "Reference",
                "FireRating",
                "AcousticRating",
                "ThermalTransmittance",
            ),
        ),
        (
            "architecture-wall-interior-loadbearing",
            (
                "IsExternal",
                "BelowTerrain",
                "Reference",
                "FireRating",
                "AcousticRating",
                "ThermalTransmittance",
            ),
        ),
        (
            "architecture-wall-exterior",
            (
                "IsExternal",
                "BelowTerrain",
                "Reference",
                "FireRating",
                "AcousticRating",
                "ThermalTransmittance",
            ),
        ),
    ],
)
def test_catalogue_attributes_link_to_wall_requirements_workflow(
    element: str, required_attributes: tuple[str, ...]
) -> None:
    attributes = _attributes(element)

    for name in required_attributes:
        assert name in attributes, f"{element}: missing {name}"
        assert WORKFLOW_ID in attributes[name].get("needed_for_workflows", []), (
            f"{element}.{name}: wall requirements workflow is not linked"
        )
