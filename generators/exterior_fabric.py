"""Exterior wall / cladding / door / window catalog generators.

Reuse the exterior-space vignette (balcony + facade) without IfcSpace volumes.
"""

from __future__ import annotations

from typing import Any

import ifcopenshell
import ifcopenshell.util.element as element_util
from ifcopenshell.api.geometry import assign_representation
from ifcopenshell.api.material import assign_material
from ifcopenshell.api.root import create_entity
from ifcopenshell.api.spatial import assign_container

from generators.base import assign_pset, assign_qto, get_body_context
from generators.interior_fabric import _extruded_slab_with_hole
from generators.parts import create_body_representation, create_extruded_area_solid, rect_polyline
from generators.wall import _assign_item_styles, _get_or_create_named_material, _get_or_create_surface_style

# Skylight (Oberlicht) in the roof slab of the window card (metres).
SKYLIGHT_BOUNDS = (0.55, 2.7, 1.45, 3.9)
SKYLIGHT_FRAME_WIDTH = 0.07
SKYLIGHT_UPSTAND = 0.18
SKYLIGHT_GLASS_THICKNESS = 0.03


def _find_exterior_wall(ifc_file: ifcopenshell.file) -> ifcopenshell.entity_instance:
    walls = [
        wall
        for wall in ifc_file.by_type("IfcWall")
        if getattr(wall, "PredefinedType", None) == "SOLIDWALL"
        or (wall.Name or "").endswith("-ExteriorWall")
    ]
    if not walls:
        raise ValueError("no exterior IfcWall in vignette")
    return walls[0]


def _find_cladding(ifc_file: ifcopenshell.file) -> ifcopenshell.entity_instance:
    coverings = [
        covering
        for covering in ifc_file.by_type("IfcCovering")
        if getattr(covering, "PredefinedType", None) == "CLADDING"
        or (covering.Name or "").endswith("-Cladding")
    ]
    if not coverings:
        raise ValueError("no exterior cladding IfcCovering in vignette")
    return coverings[0]


def _find_door(ifc_file: ifcopenshell.file) -> ifcopenshell.entity_instance:
    doors = list(ifc_file.by_type("IfcDoor"))
    if not doors:
        raise ValueError("no IfcDoor in vignette")
    return doors[0]


def _find_window(ifc_file: ifcopenshell.file) -> ifcopenshell.entity_instance:
    windows = list(ifc_file.by_type("IfcWindow"))
    if not windows:
        raise ValueError("no IfcWindow in vignette")
    return windows[0]


def _add_skylight(ifc_file: ifcopenshell.file) -> ifcopenshell.entity_instance:
    """Cut the roof slab and set a framed ``SKYLIGHT`` with an upstand into the hole."""
    slabs = [s for s in ifc_file.by_type("IfcSlab") if (s.Name or "").endswith("-CeilingSlab")]
    if not slabs:
        raise ValueError("no ceiling slab for the skylight in vignette")
    slab = slabs[0]
    storey = element_util.get_container(slab)
    body_context = get_body_context(ifc_file)
    z_bottom = float(slab.ObjectPlacement.RelativePlacement.Location.Coordinates[2])

    hx0, hy0, hx1, hy1 = SKYLIGHT_BOUNDS
    body = next(r for r in slab.Representation.Representations if r.RepresentationIdentifier == "Body")
    solid = body.Items[0]
    depth = float(solid.Depth)
    outer = [tuple(p.Coordinates[:2]) for p in solid.SweptArea.OuterCurve.Points][:4]
    body.Items = [
        _extruded_slab_with_hole(
            ifc_file,
            outer=outer,
            hole=[(hx0, hy0), (hx0, hy1), (hx1, hy1), (hx1, hy0)],
            depth=depth,
        )
    ]

    top = z_bottom + depth + SKYLIGHT_UPSTAND
    fw = SKYLIGHT_FRAME_WIDTH
    frame_solids = [
        create_extruded_area_solid(ifc_file, rect_polyline(*bounds), top - z_bottom, origin=(0.0, 0.0, z_bottom))
        for bounds in (
            (hx0, hy0, hx1, hy0 + fw),
            (hx0, hy1 - fw, hx1, hy1),
            (hx0, hy0 + fw, hx0 + fw, hy1 - fw),
            (hx1 - fw, hy0 + fw, hx1, hy1 - fw),
        )
    ]
    skylight = create_entity(ifc_file, ifc_class="IfcWindow", name="OL-01", predefined_type="SKYLIGHT")
    assign_container(ifc_file, relating_structure=storey, products=[skylight])
    assign_representation(
        ifc_file,
        product=skylight,
        representation=create_body_representation(ifc_file, body_context, frame_solids),
    )
    skylight.OverallWidth = hx1 - hx0
    skylight.OverallHeight = hy1 - hy0
    _assign_item_styles(
        ifc_file, frame_solids, _get_or_create_surface_style(ifc_file, name="Frame", rgb=(1.0, 1.0, 1.0), transparency=0.0)
    )

    glass_solid = create_extruded_area_solid(
        ifc_file,
        rect_polyline(hx0 + fw, hy0 + fw, hx1 - fw, hy1 - fw),
        SKYLIGHT_GLASS_THICKNESS,
        origin=(0.0, 0.0, top - 2.0 * SKYLIGHT_GLASS_THICKNESS),
    )
    glass = create_entity(ifc_file, ifc_class="IfcPlate", name="OL-01-Glass", predefined_type="CURTAIN_PANEL")
    glass.ObjectType = "Glass"
    assign_container(ifc_file, relating_structure=storey, products=[glass])
    assign_representation(
        ifc_file,
        product=glass,
        representation=create_body_representation(ifc_file, body_context, glass_solid),
    )
    _assign_item_styles(
        ifc_file, [glass_solid], _get_or_create_surface_style(ifc_file, name="Glass", rgb=(0.7, 0.85, 0.95), transparency=0.7)
    )
    assign_material(ifc_file, products=[glass], material=_get_or_create_named_material(ifc_file, name="Glass", category="glass"))
    return skylight


_FINDERS = {
    "wall": _find_exterior_wall,
    "cladding": _find_cladding,
    "door": _find_door,
    "window": _find_window,
}


def generate_exterior_fabric(
    params: dict[str, Any],
) -> tuple[ifcopenshell.file, ifcopenshell.entity_instance]:
    """Build the exterior-space fabric without spaces; accent one facade product.

    ``accent`` is one of ``wall``, ``cladding``, ``door``, ``window``.
    Geometry matches ``space-exterior-01``; attributes come from the element YAML.
    The window accent also sets a skylight into the roof slab and returns both
    windows so both stay accented.
    """
    from generators.space import generate_space

    space_params = dict(params.get("space_params") or {})
    if not space_params:
        raise ValueError("space_params is required (reuse the exterior-space vignette)")
    space_params.setdefault("with_context", True)
    space_params.setdefault("vignette", "exterior")
    space_params["omit_primary_space"] = True
    space_params["include_interior_space"] = False

    accent = str(params.get("accent") or "wall").lower()
    finder = _FINDERS.get(accent)
    if finder is None:
        raise ValueError(
            f"unsupported accent={accent!r}; expected one of {sorted(_FINDERS)}"
        )

    ifc_file, _handle = generate_space(space_params)
    primary = finder(ifc_file)

    name = params.get("name") or params.get("Name")
    if name:
        primary.Name = str(name)

    predefined_type = params.get("predefined_type") or params.get("PredefinedType")
    if predefined_type is not None and hasattr(primary, "PredefinedType"):
        primary.PredefinedType = str(predefined_type)

    object_type = params.get("object_type") or params.get("ObjectType")
    if object_type is not None and hasattr(primary, "ObjectType"):
        primary.ObjectType = str(object_type)

    quantities = params.get("quantities") or {}
    for qto_name, props in quantities.items():
        assign_qto(ifc_file, primary, qto_name, props)

    property_datatypes = params.get("property_datatypes") or {}
    for pset_name, props in (params.get("properties") or {}).items():
        assign_pset(
            ifc_file,
            primary,
            pset_name,
            props,
            datatypes=property_datatypes.get(pset_name),
        )

    if accent == "window" and space_params.get("include_ceiling_slab", True):
        return ifc_file, [primary, _add_skylight(ifc_file)]
    return ifc_file, primary
