"""Surrounding neighbour buildings as simple gross volumes around a project mass."""

from __future__ import annotations

from typing import Any, Sequence

import ifcopenshell
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity
from ifcopenshell.api.spatial import assign_container

from generators.base import assign_pset, assign_qto, create_project_shell, get_body_context
from generators.parts import (
    create_body_representation,
    create_brep_body_representation,
    create_extruded_area_solid,
    create_faceted_brep,
    rect_polyline,
    translation_matrix,
)

# Metres — opaque project building + three neighbour volumes
DEFAULT_PLOT_THICKNESS = 0.20
DEFAULT_PROJECT_WIDTH = 8.0
DEFAULT_PROJECT_DEPTH = 7.0
DEFAULT_PROJECT_HEIGHT = 9.0
DEFAULT_GAP = 4.0
DEFAULT_NEIGHBOR_SPECS: tuple[tuple[Any, ...], ...] = (
    # name, width, depth, height, EinspracheRisiko, optional roof ("GABLE")
    ("N001", 10.0, 7.0, 12.0, "HOCH"),
    ("N002", 8.0, 6.0, 8.0, "MITTEL", "GABLE"),
    ("N003", 7.0, 5.5, 6.0, "TIEF", "GABLE"),
)

_ENTITY_FIELD_MAP = ("Name", "LongName", "Description", "PredefinedType", "ObjectType", "Phase")


def _apply_resolved_attributes(
    ifc_file: ifcopenshell.file,
    product: ifcopenshell.entity_instance,
    resolved: dict[str, Any] | None,
) -> None:
    if not resolved:
        return
    for field in _ENTITY_FIELD_MAP:
        if field in resolved and hasattr(product, field):
            setattr(product, field, resolved[field])
    property_datatypes = resolved.get("property_datatypes") or {}
    for pset_name, props in (resolved.get("properties") or {}).items():
        assign_pset(
            ifc_file,
            product,
            pset_name,
            props,
            datatypes=property_datatypes.get(pset_name),
        )
    for qto_name, quantities in (resolved.get("quantities") or {}).items():
        assign_qto(ifc_file, product, qto_name, quantities)


def _roof_kind(spec: Sequence[Any]) -> str:
    if len(spec) > 5 and spec[5]:
        return str(spec[5]).upper()
    return "FLAT"


def pitched_eave_and_rise(width: float, depth: float, height: float) -> tuple[float, float]:
    """Eave height and rise for a gable whose ridge is ``height``.

    The ridge runs along the longer plan side. Rise stays readable in the
    catalog picture and leaves the walls as the larger part of the volume.
    """
    span = min(float(width), float(depth))
    rise = min(0.40 * span, 0.38 * float(height))
    if rise >= height or rise <= 0.0:
        rise = float(height) * 0.35
    return float(height) - rise, rise


def neighbor_gross_volume(
    width: float,
    depth: float,
    height: float,
    roof: str = "FLAT",
) -> float:
    """Gross volume of a box, or of a box with a gable up to ``height``."""
    area = float(width) * float(depth)
    if str(roof).upper() == "GABLE":
        _eave, rise = pitched_eave_and_rise(width, depth, height)
        return area * (float(height) - 0.5 * rise)
    return area * float(height)


def _add_extruded_on_site(
    ifc_file: ifcopenshell.file,
    *,
    ifc_class: str,
    name: str,
    body_context: ifcopenshell.entity_instance,
    site: ifcopenshell.entity_instance,
    polyline: Sequence[Sequence[float]],
    thickness: float,
    z_bottom: float = 0.0,
    predefined_type: str | None = None,
) -> ifcopenshell.entity_instance:
    product = create_entity(
        ifc_file,
        ifc_class=ifc_class,
        name=name,
        predefined_type=predefined_type,
    )
    assign_container(ifc_file, relating_structure=site, products=[product])
    edit_object_placement(
        ifc_file,
        product=product,
        matrix=translation_matrix(z=z_bottom),
    )
    solid = create_extruded_area_solid(
        ifc_file,
        [(float(p[0]), float(p[1])) for p in polyline],
        float(thickness),
    )
    representation = create_body_representation(ifc_file, body_context, solid)
    assign_representation(ifc_file, product=product, representation=representation)
    return product


def _gable_volume_solid(
    ifc_file: ifcopenshell.file,
    *,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    height: float,
) -> ifcopenshell.entity_instance:
    """Closed gross volume: walls to the eaves and a gable up to ``height``."""
    eave, _rise = pitched_eave_and_rise(x1 - x0, y1 - y0, height)
    ridge = float(height)
    along_x = (x1 - x0) >= (y1 - y0)
    if along_x:
        mid = (y0 + y1) * 0.5
        verts = [
            (x0, y0, 0.0),
            (x1, y0, 0.0),
            (x1, y1, 0.0),
            (x0, y1, 0.0),
            (x0, y0, eave),
            (x1, y0, eave),
            (x1, y1, eave),
            (x0, y1, eave),
            (x0, mid, ridge),
            (x1, mid, ridge),
        ]
        faces = [
            (0, 3, 2, 1),  # bottom
            (0, 1, 5, 4),  # eave wall, y0
            (3, 7, 6, 2),  # eave wall, y1
            (0, 4, 7, 3),  # gable wall, x0
            (4, 8, 7),  # gable, x0
            (1, 2, 6, 5),  # gable wall, x1
            (5, 6, 9),  # gable, x1
            (4, 5, 9, 8),  # slope toward y0
            (7, 8, 9, 6),  # slope toward y1
        ]
    else:
        mid = (x0 + x1) * 0.5
        verts = [
            (x0, y0, 0.0),
            (x1, y0, 0.0),
            (x1, y1, 0.0),
            (x0, y1, 0.0),
            (x0, y0, eave),
            (x1, y0, eave),
            (x1, y1, eave),
            (x0, y1, eave),
            (mid, y0, ridge),
            (mid, y1, ridge),
        ]
        faces = [
            (0, 3, 2, 1),
            (0, 4, 7, 3),  # eave wall, x0
            (1, 2, 6, 5),  # eave wall, x1
            (0, 1, 5, 4),  # gable wall, y0
            (4, 5, 8),  # gable, y0
            (3, 7, 6, 2),  # gable wall, y1
            (7, 9, 6),  # gable, y1
            (4, 8, 9, 7),  # slope toward x0
            (5, 6, 9, 8),  # slope toward x1
        ]
    return create_faceted_brep(ifc_file, verts, faces)


def _add_brep_on_site(
    ifc_file: ifcopenshell.file,
    *,
    ifc_class: str,
    name: str,
    body_context: ifcopenshell.entity_instance,
    site: ifcopenshell.entity_instance,
    solid: ifcopenshell.entity_instance,
    predefined_type: str | None = None,
) -> ifcopenshell.entity_instance:
    product = create_entity(
        ifc_file,
        ifc_class=ifc_class,
        name=name,
        predefined_type=predefined_type,
    )
    assign_container(ifc_file, relating_structure=site, products=[product])
    edit_object_placement(
        ifc_file,
        product=product,
        matrix=translation_matrix(z=0.0),
    )
    representation = create_brep_body_representation(ifc_file, body_context, solid)
    assign_representation(ifc_file, product=product, representation=representation)
    return product


def generate_surrounding_building(
    params: dict[str, Any],
) -> tuple[ifcopenshell.file, list[ifcopenshell.entity_instance]]:
    """Build neighbour gross volumes around an opaque project building.

    Layout: project mass centred on the plot; three neighbour volumes to the
    west, north, and east. N002 and N003 are gabled (eaves below the given
    ridge height); N001 stays a flat box. No facade detail.

    Returns ``(ifc_file, neighbor_proxies)``.
    """
    project_w = float(params.get("project_width", DEFAULT_PROJECT_WIDTH))
    project_d = float(params.get("project_depth", DEFAULT_PROJECT_DEPTH))
    project_h = float(params.get("project_height", DEFAULT_PROJECT_HEIGHT))
    gap = float(params.get("gap", DEFAULT_GAP))
    plot_t = float(params.get("plot_thickness", DEFAULT_PLOT_THICKNESS))

    specs = list(params.get("neighbor_specs") or DEFAULT_NEIGHBOR_SPECS)
    while len(specs) < 3:
        specs.append(DEFAULT_NEIGHBOR_SPECS[len(specs)])

    object_type = params.get("object_type") or "Umgebungsbau"
    predefined_type = params.get("predefined_type") or "USERDEFINED"

    n_west = specs[0]
    n_north = specs[1]
    n_east = specs[2]
    west_w, west_d, west_h = float(n_west[1]), float(n_west[2]), float(n_west[3])
    north_w, north_d, north_h = float(n_north[1]), float(n_north[2]), float(n_north[3])
    east_w, east_d, east_h = float(n_east[1]), float(n_east[2]), float(n_east[3])

    x0 = -west_w - gap
    x1 = project_w + gap + east_w
    y0 = -gap * 0.5
    y1 = project_d + gap + north_d
    plot_w = x1 - x0
    plot_d = y1 - y0
    _ = plot_w, plot_d

    project_name = params.get("project_name") or "Umgebungsbauten"
    ifc_file, _project, site, _building, storey, body_context = create_project_shell(
        project_name
    )
    _ = storey
    body_context = get_body_context(ifc_file) or body_context

    plot_poly = rect_polyline(x0, y0, x1, y1)
    solid = create_extruded_area_solid(ifc_file, plot_poly, plot_t)
    representation = create_body_representation(ifc_file, body_context, solid)
    edit_object_placement(
        ifc_file,
        product=site,
        matrix=translation_matrix(z=-plot_t),
    )
    assign_representation(ifc_file, product=site, representation=representation)

    # Opaque project mass (context, not accented)
    project_poly = rect_polyline(0.0, 0.0, project_w, project_d)
    _add_extruded_on_site(
        ifc_file,
        ifc_class="IfcSlab",
        name="Projektvolumen",
        body_context=body_context,
        site=site,
        polyline=project_poly,
        thickness=project_h,
        z_bottom=0.0,
        predefined_type="FLOOR",
    )

    placements = (
        # west neighbour
        (x0, 0.0, x0 + west_w, west_d, west_h, n_west),
        # north neighbour
        (
            project_w * 0.1,
            project_d + gap,
            project_w * 0.1 + north_w,
            project_d + gap + north_d,
            north_h,
            n_north,
        ),
        # east neighbour
        (
            project_w + gap,
            project_d * 0.15,
            project_w + gap + east_w,
            project_d * 0.15 + east_d,
            east_h,
            n_east,
        ),
    )

    base_props = dict(params.get("properties") or {})
    base_datatypes = dict(params.get("property_datatypes") or {})
    base_quantities = dict(params.get("quantities") or {})

    proxies: list[ifcopenshell.entity_instance] = []
    for sx0, sy0, sx1, sy1, height, spec in placements:
        name = str(spec[0])
        risk = str(spec[4]) if len(spec) > 4 else "MITTEL"
        roof = _roof_kind(spec)
        if roof == "GABLE":
            solid = _gable_volume_solid(
                ifc_file,
                x0=sx0,
                y0=sy0,
                x1=sx1,
                y1=sy1,
                height=height,
            )
            proxy = _add_brep_on_site(
                ifc_file,
                ifc_class="IfcBuildingElementProxy",
                name=name,
                body_context=body_context,
                site=site,
                solid=solid,
                predefined_type=predefined_type,
            )
        else:
            proxy = _add_extruded_on_site(
                ifc_file,
                ifc_class="IfcBuildingElementProxy",
                name=name,
                body_context=body_context,
                site=site,
                polyline=rect_polyline(sx0, sy0, sx1, sy1),
                thickness=height,
                z_bottom=0.0,
                predefined_type=predefined_type,
            )
        proxy.ObjectType = object_type

        props = {k: dict(v) for k, v in base_props.items()}
        umg = props.setdefault("Pset_UmgebungCommon", {})
        umg["EinspracheRisiko"] = risk
        datatypes = {k: dict(v) for k, v in base_datatypes.items()}
        umg_dt = datatypes.setdefault("Pset_UmgebungCommon", {})
        umg_dt.setdefault("EinspracheRisiko", "IfcLabel")

        quantities = {k: dict(v) for k, v in base_quantities.items()}
        qto = quantities.setdefault("Qto_BuildingElementProxyBaseQuantities", {})
        qto["GrossVolume"] = round(
            neighbor_gross_volume(sx1 - sx0, sy1 - sy0, height, roof),
            3,
        )

        _apply_resolved_attributes(
            ifc_file,
            proxy,
            {
                "Name": name,
                "PredefinedType": predefined_type,
                "ObjectType": object_type,
                "properties": props,
                "property_datatypes": datatypes,
                "quantities": quantities,
            },
        )
        proxies.append(proxy)

    return ifc_file, proxies
