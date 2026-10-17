"""Guard product-pass workflow identifiers and circularity mappings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ifcopenshell
import yaml
from ifcopenshell.util.element import get_psets, get_type

REPO_ROOT = Path(__file__).resolve().parents[1]
ELEMENTS_DIR = REPO_ROOT / "elements"
WORKFLOWS_DIR = REPO_ROOT / "workflows"

GTIN_WORKFLOW = "pragmaticbim:workflow/hov-product-pass-gtin"
SERIAL_WORKFLOW = "pragmaticbim:workflow/hov-product-pass-serial-number"
CIRCULARITY_WORKFLOW = "pragmaticbim:workflow/des-circularity"


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path}: expected a YAML mapping"
    return data


def _attributes() -> list[tuple[Path, dict[str, Any]]]:
    result: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(ELEMENTS_DIR.glob("*.yaml")):
        for attribute in _load(path).get("attributes") or []:
            result.append((path, attribute))
    return result


def test_product_pass_workflows_are_active_handover_workflows() -> None:
    for filename, workflow_id in (
        ("hov-product-pass-gtin.yaml", GTIN_WORKFLOW),
        ("hov-product-pass-serial-number.yaml", SERIAL_WORKFLOW),
    ):
        workflow = _load(WORKFLOWS_DIR / filename)
        assert workflow["id"] == workflow_id
        assert workflow["parent_workflow"] == "pragmaticbim:workflow/hov"
        assert workflow["status"] == "active"
        assert set(workflow["name"]) == {"de", "fr", "it", "en"}
        assert set(workflow["description"]) == {"de", "fr", "it", "en"}


def test_product_pass_identifiers_use_ifc_standard_psets() -> None:
    attributes = _attributes()
    gtins = [(path, item) for path, item in attributes if item.get("name") == "GlobalTradeItemNumber"]
    serials = [(path, item) for path, item in attributes if item.get("name") == "SerialNumber"]

    assert len(gtins) == 63
    assert len(serials) == 63

    for path, attribute in gtins:
        assert attribute["pset"] == "Pset_ManufacturerTypeInformation", path
        assert attribute["datatype"] == "IfcIdentifier", path
        workflows = set(attribute.get("needed_for_workflows") or [])
        assert {GTIN_WORKFLOW, SERIAL_WORKFLOW} <= workflows, path

    for path, attribute in serials:
        assert attribute["pset"] == "Pset_ManufacturerOccurrence", path
        assert attribute["datatype"] == "IfcIdentifier", path
        assert attribute.get("needed_for_workflows") == [SERIAL_WORKFLOW], path

    assert not [item for _, item in attributes if item.get("name") == "GTIN"]


def test_circularity_extensions_are_neutral_and_references_resolve() -> None:
    yaml_paths = [
        *ELEMENTS_DIR.glob("*.yaml"),
        *WORKFLOWS_DIR.glob("*.yaml"),
        *(REPO_ROOT / "values").glob("*.yaml"),
    ]
    assert all("CPset_Madaster" not in path.read_text(encoding="utf-8") for path in yaml_paths)

    circularity_names = {
        "Connection",
        "Accessibility",
        "Reuse",
        "MaterialOrProductId",
        "WasteCodes",
    }
    circularity_attributes = [
        (path, item)
        for path, item in _attributes()
        if item.get("name") in circularity_names
        and CIRCULARITY_WORKFLOW in (item.get("needed_for_workflows") or [])
    ]
    assert circularity_attributes
    assert all(item.get("pset") == "ePset_Circularity" for _, item in circularity_attributes)

    for slug in ("detachability-connection-type", "detachability-accessibility"):
        path = REPO_ROOT / "values" / f"{slug}.yaml"
        assert path.exists()
        assert _load(path)["id"] == f"pragmaticbim:value/{slug}"


def test_generated_product_sample_keeps_type_and_occurrence_data_separate() -> None:
    ifc_file = ifcopenshell.open(
        REPO_ROOT / "media" / "attachments" / "architecture-door-interior.ifc"
    )
    product = ifc_file.by_type("IfcDoor")[0]
    product_type = get_type(product)

    assert product_type is not None
    assert "GlobalTradeItemNumber" in get_psets(product_type)[
        "Pset_ManufacturerTypeInformation"
    ]
    assert "SerialNumber" in get_psets(product)["Pset_ManufacturerOccurrence"]
