"""Guard the width attributes the VKF 16-15 rules 005 and 006 need (issue #130)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")

# element -> {attribute name: (pset, quantity_type)}
EXPECTED = {
    "architecture-stair": {
        "ClearWidth": ("ePset_StairFlight", "pbs:quantity_type_clear_width"),
        "TreadLengthAtInnerSide": (
            "Pset_StairFlightCommon",
            "pbs:quantity_type_tread_length_at_inner_side",
        ),
    },
    "structural-stair": {
        "ClearWidth": ("ePset_Stair", "pbs:quantity_type_clear_width"),
        "TreadLengthAtInnerSide": (
            "ePset_Stair",
            "pbs:quantity_type_tread_length_at_inner_side",
        ),
    },
    "spaces-interior": {
        "EscapeRouteClearWidth": (
            "ePset_Space",
            "pbs:quantity_type_escape_route_clear_width",
        ),
    },
}

SHACL_RULES = ("005", "006", "007", "008", "009")


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attributes(element: str) -> list[dict[str, Any]]:
    return _load(f"elements/{element}.yaml")["attributes"]


@pytest.mark.parametrize(
    ("element", "name", "pset", "quantity_type"),
    [
        (e, n, pset, qty)
        for e, attrs in EXPECTED.items()
        for n, (pset, qty) in attrs.items()
    ],
)
def test_width_attribute_is_complete(
    element: str, name: str, pset: str, quantity_type: str
) -> None:
    attributes = _attributes(element)
    matches = [a for a in attributes if a["name"] == name]
    assert len(matches) == 1
    attribute = matches[0]

    assert attribute["pset"] == pset
    assert attribute["unit"] == "m"
    assert attribute["datatype"] in {"IfcPositiveLengthMeasure", "IfcLengthMeasure"}
    assert attribute["status"] == "active"
    assert all(str(attribute["definition"].get(lang) or "").strip() for lang in LANGS)
    assert attribute["quantity_type"] == quantity_type
    assert "performance_property_key" not in attribute


@pytest.mark.parametrize("element", sorted(EXPECTED))
def test_sort_orders_stay_unique(element: str) -> None:
    orders = [a["sort_order"] for a in _attributes(element)]
    assert len(orders) == len(set(orders))


@pytest.mark.parametrize("code", SHACL_RULES)
def test_width_rules_are_shacl_defined(code: str) -> None:
    path = next((ROOT / "rules").glob(f"vkf-16-15-{code}-*.yaml"))
    doc = _load(str(path.relative_to(ROOT)))
    assert doc["rule_status"] == "shacl_defined"
    assert "shacl" in doc and doc["shacl"].strip()
