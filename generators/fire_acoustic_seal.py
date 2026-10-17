"""IfcBuildingElementProxy catalog generator for fire and acoustic seals."""

from __future__ import annotations

from typing import Any

import ifcopenshell.util.element as element_util
import ifcopenshell.util.placement as placement_util
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity
from ifcopenshell.api.spatial import assign_container

from generators.base import assign_pset, assign_qto, get_body_context
from generators.opening import generate_opening
from generators.parts import create_body_representation, create_extruded_area_solid


def _opening_solid(opening):
    for representation in opening.Representation.Representations:
        if representation.RepresentationIdentifier != "Body":
            continue
        for item in representation.Items:
            if item.is_a("IfcExtrudedAreaSolid"):
                return item
    raise ValueError("opening has no extruded Body representation")


def generate_fire_acoustic_seal(params: dict[str, Any]) -> tuple:
    """Build the opening vignette and fill its opening with a proxy seal."""
    opening_params = dict(params)
    opening_params["properties"] = {}
    opening_params["property_datatypes"] = {}
    opening_params["quantities"] = {}
    opening_params["predefined_type"] = "OPENING"
    opening_params["name"] = str(params.get("opening_name") or "D-01")

    ifc_file, opening = generate_opening(opening_params)
    storey = element_util.get_container(opening)
    if storey is None:
        raise ValueError("opening has no storey container")

    seal = create_entity(
        ifc_file,
        ifc_class="IfcBuildingElementProxy",
        name=str(params.get("name") or "BS-01"),
        predefined_type="USERDEFINED",
    )
    seal.ObjectType = str(params.get("object_type") or "Brandschott")
    assign_container(ifc_file, relating_structure=storey, products=[seal])
    edit_object_placement(
        ifc_file,
        product=seal,
        matrix=placement_util.get_local_placement(opening.ObjectPlacement),
    )

    opening_solid = _opening_solid(opening)
    profile = [
        tuple(float(value) for value in point.Coordinates[:2])
        for point in opening_solid.SweptArea.OuterCurve.Points
    ]
    origin = tuple(
        float(value) for value in opening_solid.Position.Location.Coordinates
    )
    solid = create_extruded_area_solid(
        ifc_file,
        profile,
        float(opening_solid.Depth),
        origin=origin,
    )
    representation = create_body_representation(
        ifc_file, get_body_context(ifc_file), solid
    )
    assign_representation(ifc_file, product=seal, representation=representation)

    for qto_name, props in (params.get("quantities") or {}).items():
        assign_qto(ifc_file, seal, qto_name, props)

    property_datatypes = params.get("property_datatypes") or {}
    for pset_name, props in (params.get("properties") or {}).items():
        assign_pset(
            ifc_file,
            seal,
            pset_name,
            props,
            datatypes=property_datatypes.get(pset_name),
        )

    return ifc_file, seal
