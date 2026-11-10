"""One IFC4 file and one IFC2X3 file, each with a specimen per element.

Picture generators build a vignette around one accent. Those context products
would also match classification rules, and several IFC4 classes do not exist in
IFC2X3. This corpus keeps the same YAML defaults as the pictures and writes
only the classified object: Project, Site, Building and Storey on the shell,
every other element as a storey-contained product.

Body geometry is copied from ``media/attachments/{slug}.ifc``. Only products
that satisfy that element's German applicability are copied, so a wall vignette
does not bring its slabs and openings along. The copy is rebuilt entity by
entity, which lets an IFC4 or IFC4X3 solid land in an IFC2X3 file.

Past the grid, one reading section shows an office that stops at a suspended
ceiling, with the Luftraum filling the plenum up to the slab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement
from ifcopenshell.api.aggregate import assign_object
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity
from ifcopenshell.api.spatial import assign_container

from catalog.applicability import german_applicability, matches_applicability
from catalog.attach import MEDIA_ATTACHMENTS_DIR

from catalog.schema import (
    BEAM_DEFAULTS,
    BEAM_ELEMENT_SLUG,
    BUILDING_DEFAULTS,
    BUILDING_ELEMENT_SLUG,
    BUILDING_LAW_PARCEL_DEFAULTS,
    BUILDING_LAW_PARCEL_ELEMENT_SLUG,
    BUILT_IN_FURNITURE_DEFAULTS,
    BUILT_IN_FURNITURE_ELEMENT_SLUG,
    CEILING_DEFAULTS,
    CEILING_ELEMENT_SLUG,
    CLADDING_EXTERIOR_DEFAULTS,
    CLADDING_EXTERIOR_ELEMENT_SLUG,
    CLADDING_INTERIOR_DEFAULTS,
    CLADDING_INTERIOR_ELEMENT_SLUG,
    COLUMN_DEFAULTS,
    COLUMN_ELEMENT_SLUG,
    CONSTRUCTION_LOGISTICS_DEFAULTS,
    CONSTRUCTION_LOGISTICS_ELEMENT_SLUG,
    COORDINATION_ZONE_DEFAULTS,
    COORDINATION_ZONE_ELEMENT_SLUG,
    DECISION_VOLUME_DEFAULTS,
    DECISION_VOLUME_ELEMENT_SLUG,
    DETAIL_REFERENCE_DEFAULTS,
    DETAIL_REFERENCE_ELEMENT_SLUG,
    DOOR_EXTERIOR_DEFAULTS,
    DOOR_EXTERIOR_ELEMENT_SLUG,
    DOOR_INTERIOR_DEFAULTS,
    DOOR_INTERIOR_ELEMENT_SLUG,
    DRYWALL_REINFORCEMENT_DEFAULTS,
    DRYWALL_REINFORCEMENT_ELEMENT_SLUG,
    ELEMENTS_DIR,
    EXTERIOR_SPACE_ELEMENT_SLUG,
    FIRE_ACOUSTIC_SEAL_DEFAULTS,
    FIRE_ACOUSTIC_SEAL_ELEMENT_SLUG,
    FLOOR_COVERING_DEFAULTS,
    FLOOR_COVERING_ELEMENT_SLUG,
    FLOOR_COVERING_EXTERIOR_DEFAULTS,
    FLOOR_COVERING_EXTERIOR_ELEMENT_SLUG,
    FOOTING_DEFAULTS,
    FOOTING_ELEMENT_SLUG,
    FURNITURE_DEFAULTS,
    FURNITURE_ELEMENT_SLUG,
    GROSS_VOLUME_ELEMENT_SLUG,
    GROSS_VOLUME_UNIT_DEFAULTS,
    HUMUS_DEFAULTS,
    HUMUS_ELEMENT_SLUG,
    INSTALLATION_PATH_DEFAULTS,
    INSTALLATION_PATH_ELEMENT_SLUG,
    LUFTRAUM_ELEMENT_SLUG,
    MAINTENANCE_SPACE_DEFAULTS,
    MAINTENANCE_SPACE_ELEMENT_SLUG,
    MEP_DEVICE_DEFAULTS,
    MOVEMENT_CLEARANCE_DEFAULTS,
    MOVEMENT_CLEARANCE_ELEMENT_SLUG,
    OPENING_DEFAULTS,
    OPENING_ELEMENT_SLUG,
    OPENING_STRUCTURAL_ELEMENT_SLUG,
    PLANNING_CONSTRAINT_DEFAULTS,
    PLANNING_CONSTRAINT_ELEMENT_SLUG,
    PROJECT_DEFAULTS,
    PROJECT_ELEMENT_SLUG,
    RAILING_DEFAULTS,
    RAILING_ELEMENT_SLUG,
    RETENTION_DEFAULTS,
    RETENTION_ELEMENT_SLUG,
    ROOF_OVERFLOW_DEFAULTS,
    ROOF_OVERFLOW_ELEMENT_SLUG,
    ROOF_PITCHED_DEFAULTS,
    ROOF_PITCHED_ELEMENT_SLUG,
    ROOFING_DEFAULTS,
    ROOFING_ELEMENT_SLUG,
    SHADING_DEVICE_DEFAULTS,
    SHADING_DEVICE_ELEMENT_SLUG,
    SITE_DEFAULTS,
    SITE_ELEMENT_SLUG,
    SLAB_BALCONY_DEFAULTS,
    SLAB_BALCONY_ELEMENT_SLUG,
    SLAB_BASE_DEFAULTS,
    SLAB_BASE_ELEMENT_SLUG,
    SLAB_FLOOR_DEFAULTS,
    SLAB_FLOOR_ELEMENT_SLUG,
    SLAB_ROOF_DEFAULTS,
    SLAB_ROOF_ELEMENT_SLUG,
    SPACE_ELEMENT_SLUG,
    STAIR_DEFAULTS,
    STAIR_ELEMENT_SLUG,
    STOREY_ELEMENT_SLUG,
    STRUCTURAL_BEAM_DEFAULTS,
    STRUCTURAL_BEAM_ELEMENT_SLUG,
    STRUCTURAL_COLUMN_DEFAULTS,
    STRUCTURAL_COLUMN_ELEMENT_SLUG,
    STRUCTURAL_EDGE_STRIP_DEFAULTS,
    STRUCTURAL_EDGE_STRIP_ELEMENT_SLUG,
    STRUCTURAL_EXCLUSION_ZONE_DEFAULTS,
    STRUCTURAL_EXCLUSION_ZONE_ELEMENT_SLUG,
    STRUCTURAL_FOOTING_DEFAULTS,
    STRUCTURAL_FOOTING_ELEMENT_SLUG,
    STRUCTURAL_RAMP_DEFAULTS,
    STRUCTURAL_RAMP_ELEMENT_SLUG,
    STRUCTURAL_REBAR_DEFAULTS,
    STRUCTURAL_REBAR_ELEMENT_SLUG,
    STRUCTURAL_SLAB_BASE_DEFAULTS,
    STRUCTURAL_SLAB_BASE_ELEMENT_SLUG,
    STRUCTURAL_SLAB_FLOOR_DEFAULTS,
    STRUCTURAL_SLAB_FLOOR_ELEMENT_SLUG,
    STRUCTURAL_SLAB_ROOF_DEFAULTS,
    STRUCTURAL_SLAB_ROOF_ELEMENT_SLUG,
    STRUCTURAL_STAIR_DEFAULTS,
    STRUCTURAL_STAIR_ELEMENT_SLUG,
    STRUCTURAL_WALL_DEFAULTS,
    STRUCTURAL_WALL_ELEMENT_SLUG,
    SURROUNDING_BUILDING_DEFAULTS,
    SURROUNDING_BUILDING_ELEMENT_SLUG,
    TREE_DEFAULTS,
    TREE_ELEMENT_SLUG,
    TURNING_RADIUS_DEFAULTS,
    TURNING_RADIUS_ELEMENT_SLUG,
    UMBAU_PERIMETER_DEFAULTS,
    UMBAU_PERIMETER_ELEMENT_SLUG,
    WALL_EXTERIOR_DEFAULTS,
    WALL_EXTERIOR_ELEMENT_SLUG,
    WALL_INTERIOR_DEFAULTS,
    WALL_INTERIOR_ELEMENT_SLUG,
    WALL_INTERIOR_LB_DEFAULTS,
    WALL_INTERIOR_LB_ELEMENT_SLUG,
    WINDOW_EXTERIOR_DEFAULTS,
    WINDOW_EXTERIOR_ELEMENT_SLUG,
    WINDOW_INTERIOR_DEFAULTS,
    WINDOW_INTERIOR_ELEMENT_SLUG,
    _EXTERIOR_SPACE_DEFAULTS,
    _ELEVATOR_DEFAULTS,
    _LUFTRAUM_DEFAULTS,
    _PARKING_DEFAULTS,
    _SPACE_DEFAULTS,
    _VORSATZSCHALE_DEFAULTS,
    build_element_attributes_from_yaml,
    load_element,
)
from generators.base import assign_pset, assign_qto, create_project_shell
from generators.parts import (
    create_body_representation,
    create_extruded_area_solid,
    rect_polyline,
)
from generators.space import (
    CEILING_COVERING_THICKNESS,
    CEILING_SLAB_THICKNESS,
    EXTERIOR_WALL_THICKNESS,
    FLOOR_COVERING_THICKNESS,
    FLOOR_SLAB_THICKNESS,
    WALL_THICKNESS,
)

# Picture generators hardcode these; the reference-point mapper does not
# resolve them through the YAML defaults dict.
_REFERENCE_POINT_DEFAULTS: dict[str, Any] = {
    "PredefinedType": "USERDEFINED",
    "ObjectType": "Bezugspunkt",
    "Name": "BP-01",
}

# Same curated defaults the catalog mappers pass into the picture generators.
_SLUG_DEFAULTS: dict[str, dict[str, Any]] = {
    SPACE_ELEMENT_SLUG: _SPACE_DEFAULTS,
    "spaces-exterior": _EXTERIOR_SPACE_DEFAULTS,
    "spaces-parking": _PARKING_DEFAULTS,
    "spaces-elevator": _ELEVATOR_DEFAULTS,
    "spaces-vorsatzschale": _VORSATZSCHALE_DEFAULTS,
    "spaces-luftraum": _LUFTRAUM_DEFAULTS,
    GROSS_VOLUME_ELEMENT_SLUG: GROSS_VOLUME_UNIT_DEFAULTS["foundation"],
    CEILING_ELEMENT_SLUG: CEILING_DEFAULTS,
    FLOOR_COVERING_ELEMENT_SLUG: FLOOR_COVERING_DEFAULTS,
    FLOOR_COVERING_EXTERIOR_ELEMENT_SLUG: FLOOR_COVERING_EXTERIOR_DEFAULTS,
    PROJECT_ELEMENT_SLUG: PROJECT_DEFAULTS,
    SITE_ELEMENT_SLUG: SITE_DEFAULTS,
    BUILDING_ELEMENT_SLUG: BUILDING_DEFAULTS,
    STOREY_ELEMENT_SLUG: {"Name": "EG"},
    SLAB_BASE_ELEMENT_SLUG: SLAB_BASE_DEFAULTS,
    SLAB_FLOOR_ELEMENT_SLUG: SLAB_FLOOR_DEFAULTS,
    SLAB_ROOF_ELEMENT_SLUG: SLAB_ROOF_DEFAULTS,
    SLAB_BALCONY_ELEMENT_SLUG: SLAB_BALCONY_DEFAULTS,
    OPENING_ELEMENT_SLUG: OPENING_DEFAULTS,
    OPENING_STRUCTURAL_ELEMENT_SLUG: OPENING_DEFAULTS,
    FIRE_ACOUSTIC_SEAL_ELEMENT_SLUG: FIRE_ACOUSTIC_SEAL_DEFAULTS,
    BEAM_ELEMENT_SLUG: BEAM_DEFAULTS,
    FOOTING_ELEMENT_SLUG: FOOTING_DEFAULTS,
    COLUMN_ELEMENT_SLUG: COLUMN_DEFAULTS,
    MAINTENANCE_SPACE_ELEMENT_SLUG: MAINTENANCE_SPACE_DEFAULTS,
    INSTALLATION_PATH_ELEMENT_SLUG: INSTALLATION_PATH_DEFAULTS,
    TURNING_RADIUS_ELEMENT_SLUG: TURNING_RADIUS_DEFAULTS,
    DECISION_VOLUME_ELEMENT_SLUG: DECISION_VOLUME_DEFAULTS,
    MOVEMENT_CLEARANCE_ELEMENT_SLUG: MOVEMENT_CLEARANCE_DEFAULTS,
    BUILDING_LAW_PARCEL_ELEMENT_SLUG: BUILDING_LAW_PARCEL_DEFAULTS,
    SURROUNDING_BUILDING_ELEMENT_SLUG: SURROUNDING_BUILDING_DEFAULTS,
    CONSTRUCTION_LOGISTICS_ELEMENT_SLUG: CONSTRUCTION_LOGISTICS_DEFAULTS,
    PLANNING_CONSTRAINT_ELEMENT_SLUG: PLANNING_CONSTRAINT_DEFAULTS,
    UMBAU_PERIMETER_ELEMENT_SLUG: UMBAU_PERIMETER_DEFAULTS,
    STAIR_ELEMENT_SLUG: STAIR_DEFAULTS,
    RAILING_ELEMENT_SLUG: RAILING_DEFAULTS,
    SHADING_DEVICE_ELEMENT_SLUG: SHADING_DEVICE_DEFAULTS,
    TREE_ELEMENT_SLUG: TREE_DEFAULTS,
    HUMUS_ELEMENT_SLUG: HUMUS_DEFAULTS,
    RETENTION_ELEMENT_SLUG: RETENTION_DEFAULTS,
    FURNITURE_ELEMENT_SLUG: FURNITURE_DEFAULTS,
    BUILT_IN_FURNITURE_ELEMENT_SLUG: BUILT_IN_FURNITURE_DEFAULTS,
    COORDINATION_ZONE_ELEMENT_SLUG: COORDINATION_ZONE_DEFAULTS,
    ROOF_PITCHED_ELEMENT_SLUG: ROOF_PITCHED_DEFAULTS,
    ROOFING_ELEMENT_SLUG: ROOFING_DEFAULTS,
    ROOF_OVERFLOW_ELEMENT_SLUG: ROOF_OVERFLOW_DEFAULTS,
    DETAIL_REFERENCE_ELEMENT_SLUG: DETAIL_REFERENCE_DEFAULTS,
    WALL_EXTERIOR_ELEMENT_SLUG: WALL_EXTERIOR_DEFAULTS,
    CLADDING_EXTERIOR_ELEMENT_SLUG: CLADDING_EXTERIOR_DEFAULTS,
    WALL_INTERIOR_ELEMENT_SLUG: WALL_INTERIOR_DEFAULTS,
    WALL_INTERIOR_LB_ELEMENT_SLUG: WALL_INTERIOR_LB_DEFAULTS,
    DRYWALL_REINFORCEMENT_ELEMENT_SLUG: DRYWALL_REINFORCEMENT_DEFAULTS,
    CLADDING_INTERIOR_ELEMENT_SLUG: CLADDING_INTERIOR_DEFAULTS,
    DOOR_EXTERIOR_ELEMENT_SLUG: DOOR_EXTERIOR_DEFAULTS,
    DOOR_INTERIOR_ELEMENT_SLUG: DOOR_INTERIOR_DEFAULTS,
    WINDOW_EXTERIOR_ELEMENT_SLUG: WINDOW_EXTERIOR_DEFAULTS,
    WINDOW_INTERIOR_ELEMENT_SLUG: WINDOW_INTERIOR_DEFAULTS,
    STRUCTURAL_EXCLUSION_ZONE_ELEMENT_SLUG: STRUCTURAL_EXCLUSION_ZONE_DEFAULTS,
    STRUCTURAL_BEAM_ELEMENT_SLUG: STRUCTURAL_BEAM_DEFAULTS,
    STRUCTURAL_COLUMN_ELEMENT_SLUG: STRUCTURAL_COLUMN_DEFAULTS,
    STRUCTURAL_WALL_ELEMENT_SLUG: STRUCTURAL_WALL_DEFAULTS,
    STRUCTURAL_SLAB_FLOOR_ELEMENT_SLUG: STRUCTURAL_SLAB_FLOOR_DEFAULTS,
    STRUCTURAL_SLAB_BASE_ELEMENT_SLUG: STRUCTURAL_SLAB_BASE_DEFAULTS,
    STRUCTURAL_SLAB_ROOF_ELEMENT_SLUG: STRUCTURAL_SLAB_ROOF_DEFAULTS,
    STRUCTURAL_FOOTING_ELEMENT_SLUG: STRUCTURAL_FOOTING_DEFAULTS,
    STRUCTURAL_STAIR_ELEMENT_SLUG: STRUCTURAL_STAIR_DEFAULTS,
    STRUCTURAL_RAMP_ELEMENT_SLUG: STRUCTURAL_RAMP_DEFAULTS,
    STRUCTURAL_REBAR_ELEMENT_SLUG: STRUCTURAL_REBAR_DEFAULTS,
    STRUCTURAL_EDGE_STRIP_ELEMENT_SLUG: STRUCTURAL_EDGE_STRIP_DEFAULTS,
    "survey-reference-point": _REFERENCE_POINT_DEFAULTS,
    **MEP_DEVICE_DEFAULTS,
}

_ENTITY_FIELDS = ("Name", "LongName", "ObjectType", "Phase", "PredefinedType")
_FILE_VERSION = {"ifc4": "IFC4", "ifc2x3": "IFC2X3"}
_ENTITY_KEY = {"ifc4": "entity_ifc4", "ifc2x3": "entity_ifc2x3"}
_SHELL_SLUGS = {
    PROJECT_ELEMENT_SLUG,
    SITE_ELEMENT_SLUG,
    BUILDING_ELEMENT_SLUG,
    STOREY_ELEMENT_SLUG,
}

# Attribute resolution still sees a unit box. Applicability does not read
# those quantities, and the visible body comes from the example file.
_BOX_GEOMETRY = {"height": 1.0, "area": 1.0}
_ROW_WIDTH = 80.0
_GAP = 2.0
_SCENE_GAP = 8.0
_SCENE_DEPTH = 5.0
_SCENE_FINISH_CEILING = 2.6
_SCENE_SOFFIT = 3.2
_SCENE_EXTERIOR_HEIGHT = 1.0
_SCENE_BALCONY_WIDTH = 1.5
_SCENE_OFFICE_WIDTH = 4.0
_SCENE_CORRIDOR_WIDTH = 2.0
_EXAMPLE_CACHE: dict[
    str, tuple[list[ifcopenshell.entity_instance], np.ndarray, np.ndarray]
] = {}


def defaults_for_slug(slug: str) -> dict[str, Any]:
    """Curated picture defaults, or the slug as Name when none exist.

    An empty defaults dict would fall through to the interior-space defaults
    inside attribute resolution. A one-key dict keeps that from happening.
    """
    curated = _SLUG_DEFAULTS.get(slug)
    if curated:
        return dict(curated)
    return {"Name": slug}


def iter_elements() -> list[tuple[str, dict[str, Any]]]:
    """Active element definitions, sorted by slug."""
    items: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(ELEMENTS_DIR.glob("*.yaml")):
        element = load_element(path.stem)
        if element.get("status") not in (None, "active"):
            continue
        items.append((path.stem, element))
    return items


def generate_classification_corpus(
    ifc_schema: str = "ifc4",
) -> tuple[ifcopenshell.file, dict[str, ifcopenshell.entity_instance]]:
    """Build one project containing a specimen of every active element.

    Returns the file and a slug → entity map. ``Description`` is the slug when
    the element YAML did not set one.
    """
    schema = ifc_schema.lower()
    if schema not in _FILE_VERSION:
        raise ValueError(f"unsupported ifc_schema: {ifc_schema!r}")

    ifc_file, project, site, building, storey, body_context = create_project_shell(
        "Classification corpus",
        storey_name="EG",
        version=_FILE_VERSION[schema],
    )
    shell = {
        PROJECT_ELEMENT_SLUG: project,
        SITE_ELEMENT_SLUG: site,
        BUILDING_ELEMENT_SLUG: building,
        STOREY_ELEMENT_SLUG: storey,
    }
    specimens: dict[str, ifcopenshell.entity_instance] = {}
    cursor_x = 0.0
    cursor_y = 0.0
    row_depth = 0.0
    for slug, element in iter_elements():
        try:
            sources, mins, maxs = _example_group(slug, element)
            if slug in shell:
                product = shell[slug]
                if sources:
                    cursor_x, cursor_y, row_depth = _place_example_group(
                        ifc_file,
                        sources,
                        mins=mins,
                        maxs=maxs,
                        body_context=body_context,
                        storey=storey,
                        ifc_class=product.is_a(),
                        slug=slug,
                        cursor_x=cursor_x,
                        cursor_y=cursor_y,
                        row_depth=row_depth,
                        host=product,
                    )
                _apply_attributes(ifc_file, product, slug, schema)
                specimens[slug] = product
                continue
            ifc_class = str(element[_ENTITY_KEY[schema]])
            if sources:
                products, cursor_x, cursor_y, row_depth = _place_example_group(
                    ifc_file,
                    sources,
                    mins=mins,
                    maxs=maxs,
                    body_context=body_context,
                    storey=storey,
                    ifc_class=ifc_class,
                    slug=slug,
                    cursor_x=cursor_x,
                    cursor_y=cursor_y,
                    row_depth=row_depth,
                )
                for product in products:
                    _apply_attributes(ifc_file, product, slug, schema)
                specimens[slug] = products[0]
                continue
            origin_x, origin_y, cursor_x, cursor_y, row_depth = _reserve(
                1.0, 1.0, cursor_x, cursor_y, row_depth
            )
            product = _add_product(
                ifc_file, ifc_class=ifc_class, name=slug, storey=storey
            )
            edit_object_placement(
                ifc_file, product=product, matrix=_translation(origin_x, origin_y, 0.0)
            )
            _apply_attributes(ifc_file, product, slug, schema)
            specimens[slug] = product
        except Exception as exc:
            raise RuntimeError(f"{schema} specimen {slug} failed: {exc}") from exc
    try:
        _add_reading_scene(
            ifc_file,
            schema=schema,
            storey=storey,
            body_context=body_context,
            origin_x=0.0,
            origin_y=cursor_y + row_depth + _SCENE_GAP,
        )
    except Exception as exc:
        raise RuntimeError(f"{schema} reading scene failed: {exc}") from exc
    return ifc_file, specimens


def write_classification_corpora(output_dir: Path | None = None) -> dict[str, Path]:
    """Write ``classification-ifc4.ifc`` and ``classification-ifc2x3.ifc``."""
    directory = output_dir or (Path(__file__).resolve().parents[1] / "output")
    directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for schema, filename in (
        ("ifc4", "classification-ifc4.ifc"),
        ("ifc2x3", "classification-ifc2x3.ifc"),
    ):
        ifc_file, _specimens = generate_classification_corpus(schema)
        path = directory / filename
        ifc_file.write(str(path))
        written[schema] = path
    return written


def _example_group(
    slug: str, element: dict[str, Any]
) -> tuple[list[ifcopenshell.entity_instance], np.ndarray, np.ndarray]:
    """Products in the example IFC that satisfy this element's German rule."""
    cached = _EXAMPLE_CACHE.get(slug)
    if cached is not None:
        return cached
    path = MEDIA_ATTACHMENTS_DIR / f"{slug}.ifc"
    products: list[ifcopenshell.entity_instance] = []
    if path.is_file():
        source = ifcopenshell.open(path)
        expression = german_applicability(element)
        if expression:
            for product in source.by_type("IfcProduct"):
                if not _body_representations(product):
                    continue
                if matches_applicability(
                    product,
                    expression,
                    entity_schema=source.schema,
                    exact_entity=True,
                ):
                    products.append(product)
    if products:
        mins, maxs = _group_bbox(products)
    else:
        mins = np.zeros(3)
        maxs = np.zeros(3)
    cached = (products, mins, maxs)
    _EXAMPLE_CACHE[slug] = cached
    return cached


def _body_representations(
    product: ifcopenshell.entity_instance,
) -> list[ifcopenshell.entity_instance]:
    shape = getattr(product, "Representation", None)
    if shape is None:
        return []
    return [
        representation
        for representation in shape.Representations or []
        if representation.RepresentationIdentifier == "Body" and representation.Items
    ]


def _group_bbox(
    products: list[ifcopenshell.entity_instance],
) -> tuple[np.ndarray, np.ndarray]:
    settings = _geom_settings()
    mins = np.array([np.inf, np.inf, np.inf])
    maxs = np.array([-np.inf, -np.inf, -np.inf])
    found = False
    for product in products:
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
            verts = shape.geometry.verts
        except Exception:
            continue
        if len(verts) < 3:
            continue
        points = np.array(verts, dtype=float).reshape(-1, 3)
        mins = np.minimum(mins, points.min(axis=0))
        maxs = np.maximum(maxs, points.max(axis=0))
        found = True
    if not found:
        origin = _world_matrix(products[0])[:3, 3]
        return origin.copy(), origin + 1.0
    return mins, maxs


def _geom_settings() -> ifcopenshell.geom.settings:
    settings = getattr(_geom_settings, "cached", None)
    if settings is None:
        settings = ifcopenshell.geom.settings()
        settings.set("use-world-coords", True)
        _geom_settings.cached = settings
    return settings


def _place_example_group(
    ifc_file: ifcopenshell.file,
    sources: list[ifcopenshell.entity_instance],
    *,
    mins: np.ndarray,
    maxs: np.ndarray,
    body_context: ifcopenshell.entity_instance,
    storey: ifcopenshell.entity_instance,
    ifc_class: str,
    slug: str,
    cursor_x: float,
    cursor_y: float,
    row_depth: float,
    host: ifcopenshell.entity_instance | None = None,
) -> Any:
    """Copy each source body and shift the group so its bbox min sits on the row.

    A shell host receives every body and the first source placement. Other
    elements become one product per source, keeping their relative positions.
    """
    width = float(maxs[0] - mins[0])
    depth = float(maxs[1] - mins[1])
    origin_x, origin_y, cursor_x, cursor_y, row_depth = _reserve(
        width, depth, cursor_x, cursor_y, row_depth
    )
    shift = np.array(
        [origin_x - float(mins[0]), origin_y - float(mins[1]), -float(mins[2])],
        dtype=float,
    )
    created: list[ifcopenshell.entity_instance] = []
    placed_host = False
    for source in sources:
        matrix = _world_matrix(source)
        matrix[:3, 3] += shift
        if host is not None:
            product = host
            if not placed_host:
                edit_object_placement(ifc_file, product=product, matrix=matrix)
                placed_host = True
        else:
            product = _add_product(
                ifc_file, ifc_class=ifc_class, name=slug, storey=storey
            )
            edit_object_placement(ifc_file, product=product, matrix=matrix)
            created.append(product)
        _copy_bodies(ifc_file, product, source, body_context)
    if host is not None:
        return cursor_x, cursor_y, row_depth
    return created, cursor_x, cursor_y, row_depth


def _reserve(
    width: float,
    depth: float,
    cursor_x: float,
    cursor_y: float,
    row_depth: float,
) -> tuple[float, float, float, float, float]:
    width = max(width, 0.5)
    depth = max(depth, 0.5)
    if cursor_x > 0.0 and cursor_x + width > _ROW_WIDTH:
        cursor_x = 0.0
        cursor_y += row_depth + _GAP
        row_depth = 0.0
    origin_x = cursor_x
    origin_y = cursor_y
    return origin_x, origin_y, cursor_x + width + _GAP, cursor_y, max(row_depth, depth)


def _add_product(
    ifc_file: ifcopenshell.file,
    *,
    ifc_class: str,
    name: str,
    storey: ifcopenshell.entity_instance,
) -> ifcopenshell.entity_instance:
    """Storey product. Spaces aggregate into the storey; elements are contained."""
    product = create_entity(ifc_file, ifc_class=ifc_class, name=name)
    if _is_spatial(product):
        assign_object(ifc_file, relating_object=storey, products=[product])
    else:
        assign_container(ifc_file, relating_structure=storey, products=[product])
    return product


def _copy_bodies(
    ifc_file: ifcopenshell.file,
    product: ifcopenshell.entity_instance,
    source: ifcopenshell.entity_instance,
    body_context: ifcopenshell.entity_instance,
) -> None:
    cache: dict[int, ifcopenshell.entity_instance] = {}
    for representation in _body_representations(source):
        items = [_copy_entity(ifc_file, item, cache) for item in representation.Items]
        copied = ifc_file.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body_context,
            RepresentationIdentifier="Body",
            RepresentationType=representation.RepresentationType or "SolidModel",
            Items=items,
        )
        assign_representation(ifc_file, product=product, representation=copied)


def _copy_entity(
    ifc_file: ifcopenshell.file,
    entity: ifcopenshell.entity_instance,
    cache: dict[int, ifcopenshell.entity_instance],
) -> ifcopenshell.entity_instance:
    key = entity.id()
    cached = cache.get(key)
    if cached is not None:
        return cached
    info = entity.get_info(include_identifier=False, recursive=False)
    kwargs = {}
    for name, value in info.items():
        if name in {"type", "id"} or value is None:
            continue
        kwargs[name] = _copy_value(ifc_file, value, cache)
    try:
        created = ifc_file.create_entity(entity.is_a(), **kwargs)
    except Exception as exc:
        raise RuntimeError(
            f"cannot copy {entity.is_a()} attributes {sorted(kwargs)}"
        ) from exc
    cache[key] = created
    return created


def _copy_value(
    ifc_file: ifcopenshell.file,
    value: Any,
    cache: dict[int, ifcopenshell.entity_instance],
) -> Any:
    if isinstance(value, (list, tuple)):
        return [_copy_value(ifc_file, item, cache) for item in value]
    if hasattr(value, "is_a") and hasattr(value, "id"):
        return _copy_entity(ifc_file, value, cache)
    return value


def _world_matrix(product: ifcopenshell.entity_instance) -> np.ndarray:
    placement = getattr(product, "ObjectPlacement", None)
    if placement is None:
        return np.eye(4)
    return np.array(
        ifcopenshell.util.placement.get_local_placement(placement), dtype=float
    )


def _translation(x: float, y: float, z: float) -> np.ndarray:
    matrix = np.eye(4)
    matrix[0, 3] = x
    matrix[1, 3] = y
    matrix[2, 3] = z
    return matrix


def _is_spatial(product: ifcopenshell.entity_instance) -> bool:
    if product.is_a("IfcSpatialStructureElement"):
        return True
    try:
        return bool(product.is_a("IfcSpatialElement"))
    except RuntimeError:
        return False


def _add_reading_scene(
    ifc_file: ifcopenshell.file,
    *,
    schema: str,
    storey: ifcopenshell.entity_instance,
    body_context: ifcopenshell.entity_instance,
    origin_x: float,
    origin_y: float,
) -> None:
    """Office capped at the Abhangdecke, Luftraum in the plenum, open long sides.

    X runs balcony, facade, office, partition, corridor. Y is ``_SCENE_DEPTH``.
    Finished floor is z = 0. The floor build-up hangs below it.
    """
    depth = _SCENE_DEPTH
    finish = _SCENE_FINISH_CEILING
    soffit = _SCENE_SOFFIT
    x_facade = _SCENE_BALCONY_WIDTH
    x_office = x_facade + EXTERIOR_WALL_THICKNESS
    x_partition = x_office + _SCENE_OFFICE_WIDTH
    x_corridor = x_partition + WALL_THICKNESS
    x_end = x_corridor + _SCENE_CORRIDOR_WIDTH
    z_covering = -FLOOR_COVERING_THICKNESS
    z_slab = z_covering - FLOOR_SLAB_THICKNESS
    z_ceiling_top = soffit + CEILING_SLAB_THICKNESS

    def add(
        slug: str,
        x0: float,
        x1: float,
        z0: float,
        height: float,
        entry: dict[str, Any] | None = None,
    ) -> ifcopenshell.entity_instance:
        z0 = round(z0, 2)
        height = round(height, 2)
        ifc_class = str(load_element(slug)[_ENTITY_KEY[schema]])
        product = _add_product(
            ifc_file, ifc_class=ifc_class, name=slug, storey=storey
        )
        edit_object_placement(
            ifc_file,
            product=product,
            matrix=_translation(origin_x, origin_y, 0.0),
        )
        solid = create_extruded_area_solid(
            ifc_file,
            rect_polyline(x0, 0.0, x1, depth),
            height,
            origin=(0.0, 0.0, z0),
        )
        assign_representation(
            ifc_file,
            product=product,
            representation=create_body_representation(ifc_file, body_context, solid),
        )
        _apply_attributes(
            ifc_file,
            product,
            slug,
            schema,
            geometry={"height": height, "area": (x1 - x0) * depth},
            entry=entry,
        )
        return product

    add(
        SLAB_BALCONY_ELEMENT_SLUG,
        0.0,
        x_facade,
        z_slab,
        FLOOR_SLAB_THICKNESS,
    )
    add(
        FLOOR_COVERING_EXTERIOR_ELEMENT_SLUG,
        0.0,
        x_facade,
        z_covering,
        FLOOR_COVERING_THICKNESS,
    )
    add(
        EXTERIOR_SPACE_ELEMENT_SLUG,
        0.0,
        x_facade,
        0.0,
        _SCENE_EXTERIOR_HEIGHT,
    )
    add(SLAB_FLOOR_ELEMENT_SLUG, x_facade, x_end, z_slab, FLOOR_SLAB_THICKNESS)
    add(
        SLAB_FLOOR_ELEMENT_SLUG,
        x_facade,
        x_end,
        soffit,
        CEILING_SLAB_THICKNESS,
    )
    add(
        WALL_EXTERIOR_ELEMENT_SLUG,
        x_facade,
        x_office,
        z_slab,
        z_ceiling_top - z_slab,
    )
    add(
        FLOOR_COVERING_ELEMENT_SLUG,
        x_office,
        x_partition,
        z_covering,
        FLOOR_COVERING_THICKNESS,
    )
    add(SPACE_ELEMENT_SLUG, x_office, x_partition, 0.0, finish)
    add(
        CEILING_ELEMENT_SLUG,
        x_office,
        x_partition,
        finish,
        CEILING_COVERING_THICKNESS,
    )
    add(
        LUFTRAUM_ELEMENT_SLUG,
        x_office,
        x_partition,
        finish,
        soffit - finish,
    )
    add(WALL_INTERIOR_ELEMENT_SLUG, x_partition, x_corridor, 0.0, soffit)
    add(
        SPACE_ELEMENT_SLUG,
        x_corridor,
        x_end,
        0.0,
        soffit,
        {"Name": "102", "LongName": "Flur", "FinishCeilingHeight": soffit},
    )


def _apply_attributes(
    ifc_file: ifcopenshell.file,
    product: ifcopenshell.entity_instance,
    slug: str,
    ifc_schema: str,
    *,
    geometry: dict[str, float] | None = None,
    entry: dict[str, Any] | None = None,
) -> None:
    if entry is None:
        entry = {"Name": "EG"} if slug == STOREY_ELEMENT_SLUG else {}
    resolved = build_element_attributes_from_yaml(
        entry=entry,
        element_slug=slug,
        defaults=defaults_for_slug(slug),
        geometry=geometry or _BOX_GEOMETRY,
        ifc_schema=ifc_schema,
    )
    declared = _declared_names(product)
    for key in _ENTITY_FIELDS:
        if key not in resolved or resolved[key] is None or key not in declared:
            continue
        _set_attr(product, key, resolved[key], slug)
    direct = resolved.get("direct") or {}
    for key, value in direct.items():
        if value is None or key not in declared:
            continue
        _set_attr(product, key, value, slug)
    datatypes = resolved.get("property_datatypes") or {}
    for pset_name, values in (resolved.get("properties") or {}).items():
        assign_pset(
            ifc_file,
            product,
            pset_name,
            values,
            datatypes=datatypes.get(pset_name),
        )
    for qto_name, values in (resolved.get("quantities") or {}).items():
        assign_qto(ifc_file, product, qto_name, values)
    yaml_described = "Description" in resolved or "Description" in direct
    if not yaml_described and "Description" in declared:
        product.Description = slug


def _declared_names(product: ifcopenshell.entity_instance) -> set[str]:
    schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name(product.file.schema)
    declaration = schema.declaration_by_name(product.is_a())
    return {attribute.name() for attribute in declaration.all_attributes()}


def _set_attr(
    product: ifcopenshell.entity_instance, key: str, value: Any, slug: str
) -> None:
    """Set an entity field. An IFC4X3-only predefined type becomes USERDEFINED.

    IFC4 ``IfcGeographicElement`` has no ``VEGETATION`` token. The tree rule
    classifies that case as ``USERDEFINED`` plus ``ObjectType``.
    """
    try:
        setattr(product, key, value)
        return
    except Exception as exc:
        if key == "PredefinedType":
            try:
                setattr(product, key, "USERDEFINED")
                return
            except Exception:
                pass
        raise RuntimeError(
            f"{slug}: cannot set {product.is_a()}.{key}={value!r}"
        ) from exc


if __name__ == "__main__":
    for schema, path in write_classification_corpora().items():
        print(f"{schema}: {path}")
