"""Bauenvelope is a Name on Rahmenbedingung, not its own element."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ELEMENT_ID = "pragmaticbim:element/architecture-planning-constraint"


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_bauenvelope_is_a_planning_constraint_name() -> None:
    assert not (ROOT / "elements/architecture-bauenvelope.yaml").exists()
    assert not (ROOT / "values/objecttype-bauenvelope.yaml").exists()

    element = _load("elements/architecture-planning-constraint.yaml")
    attributes = {attribute["name"]: attribute for attribute in element["attributes"]}
    names = _load("values/name-planning-constraint.yaml")
    object_type = _load("values/objecttype-planning-constraint.yaml")

    assert element["id"] == ELEMENT_ID
    assert attributes["Name"]["allowed_values"] == (
        "pragmaticbim:value/name-planning-constraint"
    )
    assert attributes["ObjectType"]["allowed_values"] == (
        "pragmaticbim:value/objecttype-planning-constraint"
    )
    assert names["values"]["de"][0] == "Bauenvelope"
    assert names["values"]["fr"][0] == "Gabarit"
    assert names["values"]["it"][0] == "Sagoma"
    assert names["values"]["en"][0] == "Buildable envelope"
    assert object_type["values"]["de"] == ["Rahmenbedingung"]
    assert "`USERDEFINED`" in attributes["PredefinedType"]["definition"]["de"]
    assert "ObjectType=Rahmenbedingung" in element["applicability"]["de"]

    model = _load("models/surroundings.yaml")
    assert ELEMENT_ID in model["included_elements"]
    assert "pragmaticbim:element/architecture-bauenvelope" not in model["included_elements"]
