"""Quantity types used by rules and element attributes exist in the data contract (#162)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
# Pinned QuantityType enum of the data contract (no network). Documented in the fixture itself.
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "contract_quantity_types.yaml"
# Optional sibling checkout; when present the pinned list is cross-checked against it.
CONTRACT_DIR = REPO_ROOT.parents[1] / "pragmatic-bim-data-contract"

QUANTITY_TYPE = re.compile(r"pbs:quantity_type_[A-Za-z0-9_]+")


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def _pinned() -> dict[str, str]:
    return _load(FIXTURE)["quantity_types"]


def unknown_quantity_types(used: set[str], pinned: dict[str, str]) -> set[str]:
    return used - set(pinned.values())


def _rule_usages() -> list[tuple[str, str]]:
    usages = []
    for path in sorted((REPO_ROOT / "rules").glob("*.yaml")):
        shacl = _load(path).get("shacl") or ""
        usages += [(path.stem, qt) for qt in sorted(set(QUANTITY_TYPE.findall(shacl)))]
    return usages


def _attribute_usages() -> list[tuple[str, str]]:
    usages = []
    for path in sorted((REPO_ROOT / "elements").glob("*.yaml")):
        for attribute in _load(path).get("attributes") or []:
            if attribute.get("quantity_type"):
                usages.append((f"{path.stem}.{attribute['name']}", attribute["quantity_type"]))
    return usages


PINNED = _pinned()
RULE_USAGES = _rule_usages()
ATTRIBUTE_USAGES = _attribute_usages()


def test_usages_are_found() -> None:
    assert RULE_USAGES, "no rule names a pbs:quantity_type_*; the scan is broken"
    assert ATTRIBUTE_USAGES, "no element attribute has a quantity_type; the scan is broken"


@pytest.mark.parametrize(("rule", "quantity_type"), RULE_USAGES, ids=[f"{r}:{q}" for r, q in RULE_USAGES])
def test_rule_quantity_type_is_in_contract(rule: str, quantity_type: str) -> None:
    assert not unknown_quantity_types({quantity_type}, PINNED), (
        f"{rule}: {quantity_type} is not a data contract QuantityType"
    )


@pytest.mark.parametrize(
    ("attribute", "quantity_type"), ATTRIBUTE_USAGES, ids=[f"{a}:{q}" for a, q in ATTRIBUTE_USAGES]
)
def test_attribute_quantity_type_is_in_contract(attribute: str, quantity_type: str) -> None:
    assert not unknown_quantity_types({quantity_type}, PINNED), (
        f"{attribute}: {quantity_type} is not a data contract QuantityType"
    )


def test_unknown_quantity_type_is_reported() -> None:
    used = {"pbs:quantity_type_escape_route_length", "pbs:quantity_type_escape_route_lenght"}
    assert unknown_quantity_types(used, PINNED) == {"pbs:quantity_type_escape_route_lenght"}


def test_pinned_list_matches_sibling_contract() -> None:
    fixture = _load(FIXTURE)
    enums_path = CONTRACT_DIR / fixture["path"]
    if not enums_path.is_file():
        pytest.skip("no sibling data-contract checkout; using the pinned quantity types only")
    values = _load(enums_path)["enums"][fixture["enum"]]["permissible_values"]
    contract = {key: (value or {}).get("meaning") for key, value in values.items()}
    assert contract == fixture["quantity_types"], (
        "pinned quantity types differ from the sibling contract; refresh tests/fixtures/contract_quantity_types.yaml"
    )
