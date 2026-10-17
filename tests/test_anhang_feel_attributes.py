"""Keep the attributes used by Anhang D FEEL available in the catalogue."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
TYPING_WORKFLOWS = {
    "pragmaticbim:workflow/des-element-based-cost-late",
    "pragmaticbim:workflow/bes-element-based-tendering",
}


def _attributes(element: str) -> dict[str, dict]:
    path = ROOT / "elements" / f"{element}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {attribute["name"]: attribute for attribute in data["attributes"]}


TYPING_REQUIREMENTS = {
    "architecture-wall-interior": {
        "IsExternal": "Pset_WallCommon",
        "BelowTerrain": "ePset_Cost",
        "Width": "Qto_WallBaseQuantities",
        "FireRating": "Pset_WallCommon",
        "AcousticRating": "Pset_WallCommon",
        "ThermalTransmittance": "Pset_WallCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-wall-interior-loadbearing": {
        "IsExternal": "Pset_WallCommon",
        "BelowTerrain": "ePset_Cost",
        "Width": "Qto_WallBaseQuantities",
        "FireRating": "Pset_WallCommon",
        "AcousticRating": "Pset_WallCommon",
        "ThermalTransmittance": "Pset_WallCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-wall-exterior": {
        "IsExternal": "Pset_WallCommon",
        "BelowTerrain": "ePset_Cost",
        "Width": "Qto_WallBaseQuantities",
        "FireRating": "Pset_WallCommon",
        "AcousticRating": "Pset_WallCommon",
        "ThermalTransmittance": "Pset_WallCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-slab-base": {
        "Width": "Qto_SlabBaseQuantities",
        "FireRating": "Pset_SlabCommon",
        "AcousticRating": "Pset_SlabCommon",
        "ThermalTransmittance": "Pset_SlabCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-slab-floor": {
        "Width": "Qto_SlabBaseQuantities",
        "FireRating": "Pset_SlabCommon",
        "AcousticRating": "Pset_SlabCommon",
        "ThermalTransmittance": "Pset_SlabCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-slab-flat-roof": {
        "Width": "Qto_SlabBaseQuantities",
        "FireRating": "Pset_SlabCommon",
        "AcousticRating": "Pset_SlabCommon",
        "ThermalTransmittance": "Pset_SlabCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-slab-balcony": {
        "Width": "Qto_SlabBaseQuantities",
        "FireRating": "Pset_SlabCommon",
        "AcousticRating": "Pset_SlabCommon",
        "ThermalTransmittance": "Pset_SlabCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-footing": {
        "PredefinedType": None,
        "Width": "Qto_FootingBaseQuantities",
        "Height": "Qto_FootingBaseQuantities",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-column": {
        "Profilname": "ePset_Cost",
        "Width": "ePset_Cost",
        "Height": "ePset_Cost",
        "Length": "Qto_ColumnBaseQuantities",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-beam": {
        "Profilname": "ePset_Cost",
        "Width": "ePset_Cost",
        "Height": "ePset_Cost",
        "Length": "Qto_BeamBaseQuantities",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-stair": {
        "PredefinedType": None,
        "Width": "ePset_Cost",
        "Height": "ePset_Cost",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-door-exterior": {
        "PredefinedType": None,
        "IsExternal": "Pset_DoorCommon",
        "OperationType": None,
        "OverallWidth": None,
        "OverallHeight": None,
        "FireRating": "Pset_DoorCommon",
        "AcousticRating": "Pset_DoorCommon",
        "ThermalTransmittance": "Pset_DoorCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-door-interior": {
        "PredefinedType": None,
        "IsExternal": "Pset_DoorCommon",
        "OperationType": None,
        "OverallWidth": None,
        "OverallHeight": None,
        "FireRating": "Pset_DoorCommon",
        "AcousticRating": "Pset_DoorCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-window-exterior": {
        "PredefinedType": None,
        "IsExternal": "Pset_WindowCommon",
        "OverallWidth": None,
        "OverallHeight": None,
        "FireRating": "Pset_WindowCommon",
        "AcousticRating": "Pset_WindowCommon",
        "ThermalTransmittance": "Pset_WindowCommon",
        "CalculatedType": "ePset_Cost",
    },
    "architecture-window-interior": {
        "PredefinedType": None,
        "IsExternal": "Pset_WindowCommon",
        "OverallWidth": None,
        "OverallHeight": None,
        "FireRating": "Pset_WindowCommon",
        "AcousticRating": "Pset_WindowCommon",
        "CalculatedType": "ePset_Cost",
    },
}


@pytest.mark.parametrize(
    ("element", "requirements"),
    TYPING_REQUIREMENTS.items(),
)
def test_feel_typing_attributes_are_active_and_workflow_linked(
    element: str, requirements: dict[str, str | None]
) -> None:
    attributes = _attributes(element)

    for name, pset in requirements.items():
        assert name in attributes, f"{element}: missing FEEL attribute {name}"
        attribute = attributes[name]
        assert attribute["pset"] == pset, f"{element}.{name}: unexpected pset"
        assert attribute["status"] == "active", f"{element}.{name}: not active"
        assert TYPING_WORKFLOWS.issubset(
            set(attribute.get("needed_for_workflows", []))
        ), f"{element}.{name}: typing workflows are not linked"


METRIC_REQUIREMENTS = {
    "spaces-gross-volume": {
        "ObjectType": None,
        "GrossFloorArea": "Qto_SpaceBaseQuantities",
        "GrossVolume": "Qto_SpaceBaseQuantities",
    },
    "spaces-luftraum": {
        "ObjectType": None,
        "GrossFloorArea": "Qto_SpaceBaseQuantities",
        "GrossVolume": "Qto_SpaceBaseQuantities",
    },
    "spaces-interior": {
        "LongName": None,
        "Reference": "Pset_SpaceCommon",
        "NetFloorArea": "Qto_SpaceBaseQuantities",
    },
    "spaces-exterior": {
        "LongName": None,
        "Reference": "Pset_SpaceCommon",
        "NetFloorArea": "Qto_SpaceBaseQuantities",
    },
    "spaces-parking": {
        "NetFloorArea": "Qto_SpaceBaseQuantities",
    },
}


@pytest.mark.parametrize(
    ("element", "requirements"),
    METRIC_REQUIREMENTS.items(),
)
def test_feel_metric_sources_are_active(
    element: str, requirements: dict[str, str | None]
) -> None:
    attributes = _attributes(element)

    for name, pset in requirements.items():
        assert name in attributes, f"{element}: missing FEEL source {name}"
        attribute = attributes[name]
        assert attribute["pset"] == pset, f"{element}.{name}: unexpected pset"
        assert attribute["status"] == "active", f"{element}.{name}: not active"
