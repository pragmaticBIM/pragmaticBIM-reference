"""Elements reach the product classes through ePset_Cost.ProductClass and the generated value lists."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VALUE_PREFIX = "pragmaticbim:value/"
MEP_VALUE_SETS = {"product-class-mep-terminal", "product-class-mep-unit"}

# IFC4 entity of an element -> the IFC class the contract names for the same product.
IFC_ALIASES = {
    "IfcFlowTerminal": {"IfcGasTerminal"},
}

# MEP product classes whose IFC class belongs to an element that points at the other MEP list.
# Communications appliances and unitary equipment use the unit list, so these terminal classes stay unreachable.
UNREACHABLE_CONCEPTS = {
    "MTP-DATA-WIFI-AP",
    "MTP-HEAT-FAN-COIL",
    "MTP-COOL-FAN-COIL",
}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


@lru_cache(maxsize=1)
def _schemes() -> list[dict[str, Any]]:
    return _load(REPO_ROOT / "products" / "_names.yaml")["schemes"]


@lru_cache(maxsize=1)
def _elements() -> list[dict[str, Any]]:
    return [_load(path) for path in sorted((REPO_ROOT / "elements").glob("*.yaml"))]


@lru_cache(maxsize=1)
def _product_class_attributes() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (element, attribute)
        for element in _elements()
        for attribute in element.get("attributes") or []
        if attribute.get("name") == "ProductClass"
    ]


def _value_set(attribute: dict[str, Any]) -> str:
    return str(attribute.get("allowed_values") or "").removeprefix(VALUE_PREFIX)


def _ifc_classes(concept: dict[str, Any]) -> set[str]:
    return {part.strip() for part in (concept.get("ifc_class") or "").split(",") if part.strip()}


def _entities(element: dict[str, Any]) -> set[str]:
    entity = element.get("entity_ifc4")
    return {entity, *IFC_ALIASES.get(entity, set())}


def test_every_scheme_with_sheets_has_a_value_set() -> None:
    missing = [scheme["scheme"] for scheme in _schemes() if scheme["sheets"] and not scheme.get("value_set")]
    assert not missing, f"schemes with data sheets but no value list: {missing}"


def test_every_product_class_list_is_used_by_an_element() -> None:
    used = {_value_set(attribute) for _, attribute in _product_class_attributes()}
    lists = {path.stem for path in (REPO_ROOT / "values").glob("product-class-*.yaml")}
    assert lists - used == set(), f"product class lists no element points at: {sorted(lists - used)}"


@pytest.mark.parametrize(
    "element_id",
    sorted({element["id"] for element, _ in _product_class_attributes()}),
)
def test_product_class_attribute_points_at_a_product_list(element_id: str) -> None:
    for element, attribute in _product_class_attributes():
        if element["id"] != element_id:
            continue
        value_set = _value_set(attribute)
        assert attribute.get("pset") == "ePset_Cost", f"{element_id}: ProductClass belongs in ePset_Cost"
        assert value_set.startswith("product-class-"), f"{element_id}: {attribute.get('allowed_values')}"
        assert (REPO_ROOT / "values" / f"{value_set}.yaml").exists(), f"{element_id}: missing {value_set}"


def test_mep_elements_match_a_product_class_of_their_list() -> None:
    by_value_set = {scheme["value_set"]: scheme for scheme in _schemes() if scheme.get("value_set")}
    for element, attribute in _product_class_attributes():
        value_set = _value_set(attribute)
        if value_set not in MEP_VALUE_SETS:
            continue
        classes = set().union(*(_ifc_classes(c) for c in by_value_set[value_set]["concepts"]))
        assert _entities(element) & classes, (
            f"{element['id']}: no product class in {value_set} names {element.get('entity_ifc4')}"
        )


def test_unreachable_mep_concepts_are_listed() -> None:
    by_value_set = {scheme["value_set"]: scheme for scheme in _schemes() if scheme.get("value_set")}
    entities_by_list: dict[str, set[str]] = {}
    for element, attribute in _product_class_attributes():
        entities_by_list.setdefault(_value_set(attribute), set()).update(_entities(element))
    unreachable = {
        concept["code"]
        for value_set in MEP_VALUE_SETS
        for concept in by_value_set[value_set]["concepts"]
        if concept.get("top") and not _ifc_classes(concept) & entities_by_list.get(value_set, set())
    }
    assert unreachable == UNREACHABLE_CONCEPTS, (
        f"unreachable MEP product classes changed: add {sorted(unreachable - UNREACHABLE_CONCEPTS)}, "
        f"remove {sorted(UNREACHABLE_CONCEPTS - unreachable)}"
    )
