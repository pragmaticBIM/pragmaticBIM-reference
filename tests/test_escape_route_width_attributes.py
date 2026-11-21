"""Guard the width attributes the VKF 16-15 rules 005 and 006 need (issue #125)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")

# element -> {attribute name: pset}
EXPECTED = {
    "architecture-stair": {
        "ClearWidth": "ePset_StairFlight",
        "TreadLengthAtInnerSide": "Pset_StairFlightCommon",
    },
    "structural-stair": {
        "ClearWidth": "ePset_Stair",
        "TreadLengthAtInnerSide": "ePset_Stair",
    },
    "spaces-interior": {"EscapeRouteClearWidth": "ePset_Space"},
}


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attributes(element: str) -> list[dict[str, Any]]:
    return _load(f"elements/{element}.yaml")["attributes"]


@pytest.mark.parametrize(
    ("element", "name", "pset"),
    [(e, n, p) for e, attrs in EXPECTED.items() for n, p in attrs.items()],
)
def test_width_attribute_is_complete(element: str, name: str, pset: str) -> None:
    attributes = _attributes(element)
    matches = [a for a in attributes if a["name"] == name]
    assert len(matches) == 1
    attribute = matches[0]

    assert attribute["pset"] == pset
    assert attribute["unit"] == "m"
    assert attribute["datatype"] in {"IfcPositiveLengthMeasure", "IfcLengthMeasure"}
    assert attribute["status"] == "active"
    assert all(str(attribute["definition"].get(lang) or "").strip() for lang in LANGS)
    # No contract key is invented here; that waits for the data contract (#125).
    assert "performance_property_key" not in attribute
    assert "quantity_type" not in attribute


@pytest.mark.parametrize("element", sorted(EXPECTED))
def test_sort_orders_stay_unique(element: str) -> None:
    orders = [a["sort_order"] for a in _attributes(element)]
    assert len(orders) == len(set(orders))


def test_stair_rules_stay_text_only_until_the_contract_carries_the_facts() -> None:
    for code in ("005", "006", "007", "008", "009"):
        path = next((ROOT / "rules").glob(f"vkf-16-15-{code}-*.yaml"))
        assert _load(str(path.relative_to(ROOT)))["rule_status"] != "shacl_defined"
