"""Guard the optional COBie handover profile and its curated model scope."""

from pathlib import Path
from typing import Any

import yaml


from catalog.baseline import (
    attribute_applies_to_all_workflows,
    attribute_applies_to_workflow,
    spatial_baseline_element_ids,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ELEMENTS_DIR = REPO_ROOT / "elements"
WORKFLOW_ID = "pragmaticbim:workflow/hov-cobie-data-delivery"
FM_SOURCE_WORKFLOWS = {
    "pragmaticbim:workflow/hov-fm-minimal-data-delivery",
    "pragmaticbim:workflow/hov-fm-3d-information-delivery",
}
SPATIAL_NAME_ELEMENTS = {
    "pragmaticbim:element/project",
    "pragmaticbim:element/site",
    "pragmaticbim:element/building",
    "pragmaticbim:element/storey",
}
SPATIAL_BASELINE_ELEMENTS = set(spatial_baseline_element_ids())


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def _workflows() -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / "workflows").glob("*.yaml")):
        loaded.append(_load(path))
    return loaded


def _cobie_attributes() -> list[tuple[str, dict[str, Any]]]:
    linked: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(ELEMENTS_DIR.glob("*.yaml")):
        element = _load(path)
        for attribute in element.get("attributes") or []:
            if attribute_applies_to_workflow(attribute, WORKFLOW_ID):
                linked.append((str(element["id"]), attribute))
    return linked


def test_cobie_workflow_is_an_active_international_handover_profile() -> None:
    workflow = _load(REPO_ROOT / "workflows" / "hov-cobie-data-delivery.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/hov"
    assert "countries" not in workflow
    for language in ("de", "fr", "it", "en"):
        assert "COBie" in workflow["name"][language]
        assert "COBie" in workflow["description"][language]


def test_cobie_uses_only_curated_fm_attributes_and_spatial_names() -> None:
    linked = _cobie_attributes()
    assert linked
    catalog_workflows = _workflows()

    for element_id, attribute in linked:
        workflows = set(attribute.get("needed_for_workflows") or [])
        is_spatial_name = (
            element_id in SPATIAL_NAME_ELEMENTS and attribute.get("name") == "Name"
        )
        is_spatial_baseline = (
            element_id in SPATIAL_BASELINE_ELEMENTS
            and attribute_applies_to_all_workflows(attribute, catalog_workflows)
        )
        assert (
            is_spatial_name
            or is_spatial_baseline
            or workflows & FM_SOURCE_WORKFLOWS
        ), (
            element_id,
            attribute.get("name"),
        )


def test_cobie_links_operational_assets_but_not_ordinary_construction() -> None:
    linked_elements = {element_id for element_id, _ in _cobie_attributes()}

    assert SPATIAL_NAME_ELEMENTS <= linked_elements
    assert {
        "pragmaticbim:element/spaces-interior",
        "pragmaticbim:element/architecture-door-interior",
        "pragmaticbim:element/architecture-window-exterior",
        "pragmaticbim:element/mep-pump",
        "pragmaticbim:element/mep-electric-distribution-board",
    } <= linked_elements
    assert {
        "pragmaticbim:element/architecture-wall-interior",
        "pragmaticbim:element/architecture-slab-floor",
        "pragmaticbim:element/structural-wall",
        "pragmaticbim:element/structural-beam",
    }.isdisjoint(linked_elements)
