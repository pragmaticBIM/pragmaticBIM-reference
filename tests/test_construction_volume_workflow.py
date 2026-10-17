"""Guard the construction-volume workflow and its space quantities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from catalog.baseline import attribute_applies_to_all_workflows


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/des-construction-volume"
LANGS = ("de", "fr", "it", "en")
PHASES = ["11", "21", "22", "31", "32", "33", "41", "51", "52", "53", "61", "62"]
VOLUME_LINKS = {
    "spaces-gross-volume": "GrossVolume",
    "spaces-interior": "NetVolume",
    "spaces-luftraum": "GrossVolume",
}


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attributes(element: str) -> dict[str, dict[str, Any]]:
    data = _load(f"elements/{element}.yaml")
    return {attribute["name"]: attribute for attribute in data["attributes"]}


def test_construction_volume_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/des-construction-volume.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "DES-KV"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/des"
    assert workflow["needed_in_domain"] == ["pragmaticbim:domain/architecture"]
    assert "countries" not in workflow
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_net_volume_contract() -> None:
    attribute = _attributes("spaces-interior")["NetVolume"]

    assert attribute["pset"] == "Qto_SpaceBaseQuantities"
    assert attribute["datatype"] == "IfcVolumeMeasure"
    assert attribute["unit"] == "m³"
    assert attribute["needed_in_phases"] == PHASES
    assert attribute["ifc_versions"] == ["ifc4", "ifc4x3"]
    assert attribute["status"] == "active"
    assert attribute["needed_for_workflows"] == [WORKFLOW_ID]
    assert all(str(attribute["definition"].get(lang) or "").strip() for lang in LANGS)


def test_only_the_three_space_volumes_link_the_workflow() -> None:
    workflows = [
        _load(f"workflows/{path.name}")
        for path in sorted((ROOT / "workflows").glob("*.yaml"))
    ]
    linked: set[tuple[str, str]] = set()
    for path in sorted((ROOT / "elements").glob("*.yaml")):
        element = yaml.safe_load(path.read_text(encoding="utf-8"))
        for attribute in element.get("attributes") or []:
            refs = attribute.get("needed_for_workflows") or []
            if WORKFLOW_ID not in refs:
                continue
            if attribute_applies_to_all_workflows(attribute, workflows):
                continue
            linked.add((path.stem, attribute["name"]))

    assert linked == set(VOLUME_LINKS.items())
    for element, name in VOLUME_LINKS.items():
        attribute = _attributes(element)[name]
        assert attribute["pset"] == "Qto_SpaceBaseQuantities"
        assert attribute["datatype"] == "IfcVolumeMeasure"


def test_construction_volume_is_activated_from_medium_sustainability() -> None:
    goal = _load("project_goals/verifiable-sustainability.yaml")
    levels = {level["code"]: level for level in goal["levels"]}

    assert WORKFLOW_ID not in (levels["SUS-01"].get("activated_workflows") or [])
    assert WORKFLOW_ID in levels["SUS-02"]["activated_workflows"]
    assert WORKFLOW_ID in levels["SUS-03"]["activated_workflows"]
    assert set(levels["SUS-02"]["activated_workflows"]).issubset(
        levels["SUS-03"]["activated_workflows"]
    )
