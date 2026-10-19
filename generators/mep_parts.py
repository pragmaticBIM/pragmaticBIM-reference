"""Shared helpers for MEP catalog vignettes (devices, segments, accent registry)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

import ifcopenshell
import numpy as np
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity
from ifcopenshell.api.spatial import assign_container

from catalog.schema import MEP_DEVICE_DEFAULTS, load_element
from generators.base import assign_pset, assign_qto
from generators.parts import (
    create_body_representation,
    create_extruded_area_solid,
    create_oriented_extruded_solid,
    rect_polyline,
    translation_matrix,
)
from generators.slab import add_slab
from generators.wall import add_wall

Point3 = Sequence[float]


def box_solid(
    ifc_file: ifcopenshell.file,
    x0: float,
    y0: float,
    z0: float,
    x1: float,
    y1: float,
    z1: float,
) -> ifcopenshell.entity_instance:
    """Axis-aligned box in world coordinates (product placed at the origin)."""
    lo_x, hi_x = sorted((float(x0), float(x1)))
    lo_y, hi_y = sorted((float(y0), float(y1)))
    lo_z, hi_z = sorted((float(z0), float(z1)))
    return create_extruded_area_solid(
        ifc_file,
        rect_polyline(lo_x, lo_y, hi_x, hi_y),
        hi_z - lo_z,
        origin=(0.0, 0.0, lo_z),
    )


def _circle(radius: float, segments: int) -> list[tuple[float, float]]:
    return [
        (
            radius * math.cos(2.0 * math.pi * i / segments),
            radius * math.sin(2.0 * math.pi * i / segments),
        )
        for i in range(segments)
    ]


def _axis_frame(
    start: Point3, end: Point3
) -> tuple[np.ndarray, float, tuple[float, float, float]]:
    """Unit axis, length and a horizontal (or +X) reference direction."""
    a = np.array(start, dtype=np.float64)
    b = np.array(end, dtype=np.float64)
    vector = b - a
    length = float(np.linalg.norm(vector))
    if length <= 1e-9:
        raise ValueError("segment start and end must differ")
    axis = vector / length
    if abs(axis[2]) > 0.999:
        ref = (1.0, 0.0, 0.0)
    else:
        horizontal = np.array([-axis[1], axis[0], 0.0])
        horizontal /= np.linalg.norm(horizontal)
        ref = (float(horizontal[0]), float(horizontal[1]), 0.0)
    return axis, length, ref


def pipe_solid(
    ifc_file: ifcopenshell.file,
    start: Point3,
    end: Point3,
    radius: float,
    *,
    segments: int = 8,
) -> ifcopenshell.entity_instance:
    """Round segment from ``start`` to ``end`` (any direction)."""
    axis, length, ref = _axis_frame(start, end)
    return create_oriented_extruded_solid(
        ifc_file,
        _circle(float(radius), segments),
        length,
        origin=tuple(float(v) for v in start),
        axis=tuple(float(v) for v in axis),
        ref_direction=ref,
    )


def duct_solid(
    ifc_file: ifcopenshell.file,
    start: Point3,
    end: Point3,
    width: float,
    height: float,
) -> ifcopenshell.entity_instance:
    """Rectangular segment centred on the ``start``→``end`` line.

    Horizontal runs: ``width`` is horizontal, ``height`` vertical.
    Vertical runs: ``width`` along X, ``height`` along Y.
    """
    axis, length, ref = _axis_frame(start, end)
    hw, hh = float(width) * 0.5, float(height) * 0.5
    return create_oriented_extruded_solid(
        ifc_file,
        rect_polyline(-hw, -hh, hw, hh),
        length,
        origin=tuple(float(v) for v in start),
        axis=tuple(float(v) for v in axis),
        ref_direction=ref,
    )


def vertical_cylinder_solid(
    ifc_file: ifcopenshell.file,
    cx: float,
    cy: float,
    z0: float,
    radius: float,
    height: float,
    *,
    segments: int = 12,
) -> ifcopenshell.entity_instance:
    return pipe_solid(
        ifc_file,
        (cx, cy, z0),
        (cx, cy, z0 + height),
        radius,
        segments=segments,
    )


def add_solid_product(
    ifc_file: ifcopenshell.file,
    *,
    ifc_class: str,
    name: str,
    body_context: ifcopenshell.entity_instance,
    storey: ifcopenshell.entity_instance,
    solids: Sequence[ifcopenshell.entity_instance],
    predefined_type: str | None = None,
    object_type: str | None = None,
) -> ifcopenshell.entity_instance:
    """Storey-contained product placed at the origin with world-coordinate solids."""
    product = create_entity(
        ifc_file,
        ifc_class=ifc_class,
        name=name,
        predefined_type=predefined_type,
    )
    if object_type is not None and hasattr(product, "ObjectType"):
        product.ObjectType = object_type
    assign_container(ifc_file, relating_structure=storey, products=[product])
    edit_object_placement(ifc_file, product=product, matrix=translation_matrix())
    representation = create_body_representation(ifc_file, body_context, list(solids))
    assign_representation(ifc_file, product=product, representation=representation)
    return product


def add_corner_room(
    ifc_file: ifcopenshell.file,
    *,
    body_context: ifcopenshell.entity_instance,
    storey: ifcopenshell.entity_instance,
    width: float,
    depth: float,
    wall_height: float,
    wall_thickness: float = 0.20,
    slab_thickness: float = 0.25,
    back_wall_name: str = "Rueckwand",
    side_wall_name: str = "Seitenwand",
) -> tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance, ifcopenshell.entity_instance]:
    """Floor slab with a back wall (y = 0) and a side wall (x = 0); the front corner stays open.

    Interior is ``x ∈ [0, width]``, ``y ∈ [0, depth]``, finished floor at z = 0.
    Returns ``(slab, back_wall, side_wall)``.
    """
    t = float(wall_thickness)
    slab = add_slab(
        ifc_file,
        name="Bodenplatte",
        body_context=body_context,
        storey=storey,
        polyline=rect_polyline(-t, -t, float(width), float(depth)),
        thickness=float(slab_thickness),
        z_bottom=-float(slab_thickness),
        predefined_type="FLOOR",
    )
    back = add_wall(
        ifc_file,
        name=back_wall_name,
        body_context=body_context,
        storey=storey,
        origin=(-t, -t, 0.0),
        length=float(width) + t,
        height=float(wall_height),
        thickness=t,
        direction_xy=(1.0, 0.0),
        predefined_type="SOLIDWALL",
    )
    side = add_wall(
        ifc_file,
        name=side_wall_name,
        body_context=body_context,
        storey=storey,
        origin=(0.0, 0.0, 0.0),
        length=float(depth),
        height=float(wall_height),
        thickness=t,
        direction_xy=(0.0, 1.0),
        predefined_type="SOLIDWALL",
    )
    return slab, back, side


def numbered_name(name: str, index: int) -> str:
    """``WE-01`` → ``WE-02`` for index 1; appends ``-n`` when no trailing number."""
    if index == 0:
        return name
    match = re.search(r"(\d+)$", name)
    if not match:
        return f"{name}-{index + 1}"
    digits = match.group(1)
    return f"{name[: match.start()]}{int(digits) + index:0{len(digits)}d}"


@dataclass
class _Registered:
    product: ifcopenshell.entity_instance
    name: str | None
    predefined_type: str | None
    property_overrides: dict[str, Any]
    quantities: dict[str, dict[str, Any]]


@dataclass
class MepScene:
    """Builds one MEP vignette and remembers which products belong to which element slug.

    Every device is created with the IFC4 class from its element YAML. The
    highlighted slug receives the YAML-resolved attributes in ``finish``;
    the rest stays white context with Name / PredefinedType only.
    """

    ifc_file: ifcopenshell.file
    body_context: ifcopenshell.entity_instance
    storey: ifcopenshell.entity_instance
    registry: dict[str, list[_Registered]] = field(default_factory=dict)
    dotted: list[ifcopenshell.entity_instance] = field(default_factory=list)
    thin: list[ifcopenshell.entity_instance] = field(default_factory=list)

    def device(
        self,
        slug: str,
        solids: Sequence[ifcopenshell.entity_instance],
        *,
        name: str | None = None,
        predefined_type: str | None = None,
        property_overrides: dict[str, Any] | None = None,
        quantities: dict[str, dict[str, Any]] | None = None,
    ) -> ifcopenshell.entity_instance:
        defaults = MEP_DEVICE_DEFAULTS[slug]
        ifc_class = str(load_element(slug)["entity_ifc4"])
        index = len(self.registry.get(slug, []))
        default_name = numbered_name(str(defaults.get("Name") or slug), index)
        predefined = predefined_type or defaults.get("PredefinedType")
        product = add_solid_product(
            self.ifc_file,
            ifc_class=ifc_class,
            name=name or default_name,
            body_context=self.body_context,
            storey=self.storey,
            solids=solids,
            predefined_type=predefined,
            object_type=defaults.get("ObjectType"),
        )
        self.registry.setdefault(slug, []).append(
            _Registered(
                product=product,
                name=name,
                predefined_type=predefined_type,
                property_overrides=dict(property_overrides or {}),
                quantities=dict(quantities or {}),
            )
        )
        return product

    def register(
        self,
        slug: str,
        product: ifcopenshell.entity_instance,
        *,
        name: str | None = None,
        predefined_type: str | None = None,
    ) -> ifcopenshell.entity_instance:
        """Register an existing product (e.g. reclassified vignette part) under ``slug``."""
        self.registry.setdefault(slug, []).append(
            _Registered(
                product=product,
                name=name,
                predefined_type=predefined_type,
                property_overrides={},
                quantities={},
            )
        )
        return product

    def context(
        self,
        ifc_class: str,
        name: str,
        solids: Sequence[ifcopenshell.entity_instance],
        *,
        predefined_type: str | None = None,
        object_type: str | None = None,
    ) -> ifcopenshell.entity_instance:
        return add_solid_product(
            self.ifc_file,
            ifc_class=ifc_class,
            name=name,
            body_context=self.body_context,
            storey=self.storey,
            solids=solids,
            predefined_type=predefined_type,
            object_type=object_type,
        )

    def finish(
        self, params: dict[str, Any]
    ) -> tuple[
        ifcopenshell.file,
        list[ifcopenshell.entity_instance],
        list[ifcopenshell.entity_instance],
        list[ifcopenshell.entity_instance],
    ]:
        """Apply YAML attributes to the highlighted slug; return runner tuple."""
        highlight = str(params.get("highlight") or "")
        entries = self.registry.get(highlight)
        if not entries:
            raise ValueError(f"MEP vignette has no products for highlight {highlight!r}")
        base_name = str(params.get("name") or MEP_DEVICE_DEFAULTS[highlight].get("Name") or highlight)
        predefined = params.get("predefined_type")
        object_type = params.get("object_type")
        tag = params.get("tag")
        properties = params.get("properties") or {}
        datatypes = params.get("property_datatypes") or {}
        quantities = params.get("quantities") or {}

        primary: list[ifcopenshell.entity_instance] = []
        for index, entry in enumerate(entries):
            product = entry.product
            product.Name = entry.name or numbered_name(base_name, index)
            chosen_type = entry.predefined_type or predefined
            if chosen_type and hasattr(product, "PredefinedType"):
                product.PredefinedType = chosen_type
            if object_type is not None and hasattr(product, "ObjectType"):
                product.ObjectType = object_type
            if tag is not None and hasattr(product, "Tag"):
                product.Tag = numbered_name(str(tag), index) if entry.name is None else entry.name
            for pset_name, props in properties.items():
                values = dict(props)
                for key, value in entry.property_overrides.items():
                    if key in values:
                        values[key] = value
                assign_pset(
                    self.ifc_file,
                    product,
                    pset_name,
                    values,
                    datatypes=datatypes.get(pset_name),
                )
            merged_qtos = {name: dict(values) for name, values in quantities.items()}
            for qto_name, values in entry.quantities.items():
                merged_qtos.setdefault(qto_name, {}).update(values)
            for qto_name, values in merged_qtos.items():
                assign_qto(self.ifc_file, product, qto_name, values)
            primary.append(product)
        return self.ifc_file, primary, list(self.dotted), list(self.thin)
