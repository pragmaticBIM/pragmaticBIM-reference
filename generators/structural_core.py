"""Shared shell-construction vignette for structural (Tragwerk) catalog cards.

Base slab + one wall + one column + floor slab, with flags per card. Card
generators add detail products on top of this scene and accent one of them.
All geometry is placed in world coordinates (metres).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import ifcopenshell
from ifcopenshell.api.feature import add_feature
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity
from ifcopenshell.api.spatial import assign_container

from generators.base import assign_pset, assign_qto, create_project_shell, get_body_context
from generators.parts import (
    _axis2placement3d,
    _closed_polyline_2d,
    create_body_representation,
    create_extruded_area_solid,
    rect_polyline,
    translation_matrix,
)

DEFAULT_SLAB_WIDTH = 4.0
DEFAULT_SLAB_DEPTH = 4.0
BASE_SLAB_THICKNESS = 0.30
WALL_THICKNESS = 0.25
WALL_HEIGHT = 2.60
COLUMN_SIZE = 0.30
FLOOR_SLAB_THICKNESS = 0.25
DEFAULT_COLUMN_CENTER = (2.6, 2.6)

# Drawn thicker than a real elastomer bearing so it reads at catalog size.
BEARING_PAD_THICKNESS = 0.02
BEARING_PAD_OBJECT_TYPE = "Elastomerlager"

_ENTITY_FIELD_MAP = ("Name", "LongName", "PredefinedType", "ObjectType", "Phase", "Description")


@dataclass
class StructuralCore:
    """Handles and levels of the shared structural vignette."""

    ifc_file: ifcopenshell.file
    storey: ifcopenshell.entity_instance
    body_context: ifcopenshell.entity_instance
    slab_width: float
    slab_depth: float
    base_thickness: float
    wall_thickness: float
    storey_height: float
    column_size: float
    column_center: tuple[float, float]
    floor_thickness: float
    base_slab: ifcopenshell.entity_instance | None = None
    wall: ifcopenshell.entity_instance | None = None
    column: ifcopenshell.entity_instance | None = None
    floor_slab: ifcopenshell.entity_instance | None = None
    wall_bottom: float = 0.0
    wall_body_height: float = 0.0
    wall_span: tuple[float, float] = (0.0, DEFAULT_SLAB_WIDTH)

    @property
    def base_top(self) -> float:
        return self.base_thickness

    @property
    def floor_bottom(self) -> float:
        return self.base_thickness + self.storey_height

    @property
    def floor_top(self) -> float:
        return self.floor_bottom + self.floor_thickness

    @property
    def wall_top(self) -> float:
        return self.wall_bottom + self.wall_body_height


def extrude_profile(
    ifc_file: ifcopenshell.file,
    profile: Sequence[Sequence[float]],
    depth: float,
    *,
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    axis: Sequence[float] = (0.0, 0.0, 1.0),
    ref_direction: Sequence[float] = (1.0, 0.0, 0.0),
) -> ifcopenshell.entity_instance:
    """Extrude a closed 2D profile along ``axis`` from ``origin``.

    Profile X runs along ``ref_direction``; profile Y along ``axis × ref_direction``.
    With ``axis=(1,0,0)`` and ``ref_direction=(0,1,0)`` the profile is drawn in
    world (Y, Z) and extruded along +X.
    """
    if depth <= 0:
        raise ValueError("extrusion depth must be positive")
    profile_def = ifc_file.create_entity(
        "IfcArbitraryClosedProfileDef",
        ProfileType="AREA",
        ProfileName=None,
        OuterCurve=_closed_polyline_2d(ifc_file, profile),
    )
    return ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile_def,
        Position=_axis2placement3d(ifc_file, origin, axis=axis, ref_direction=ref_direction),
        ExtrudedDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=float(depth),
    )


def extrude_yz_along_x(
    ifc_file: ifcopenshell.file,
    profile_yz: Sequence[Sequence[float]],
    *,
    x0: float,
    length: float,
) -> ifcopenshell.entity_instance:
    """Extrude a profile drawn in world (Y, Z) along +X from ``x0``."""
    return extrude_profile(
        ifc_file,
        profile_yz,
        length,
        origin=(x0, 0.0, 0.0),
        axis=(1.0, 0.0, 0.0),
        ref_direction=(0.0, 1.0, 0.0),
    )


def extrude_with_voids(
    ifc_file: ifcopenshell.file,
    outer: Sequence[Sequence[float]],
    inners: Sequence[Sequence[Sequence[float]]],
    depth: float,
    *,
    z_bottom: float = 0.0,
) -> ifcopenshell.entity_instance:
    """Vertical extrusion of a plan polygon with holes (e.g. pit in a base slab)."""
    profile_def = ifc_file.create_entity(
        "IfcArbitraryProfileDefWithVoids",
        ProfileType="AREA",
        ProfileName=None,
        OuterCurve=_closed_polyline_2d(ifc_file, outer),
        InnerCurves=[_closed_polyline_2d(ifc_file, inner) for inner in inners],
    )
    return ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile_def,
        Position=_axis2placement3d(ifc_file, (0.0, 0.0, float(z_bottom))),
        ExtrudedDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=float(depth),
    )


def box_solid(
    ifc_file: ifcopenshell.file,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    z0: float,
    z1: float,
) -> ifcopenshell.entity_instance:
    return create_extruded_area_solid(
        ifc_file, rect_polyline(x0, y0, x1, y1), z1 - z0, origin=(0.0, 0.0, z0)
    )


def bar_solid(
    ifc_file: ifcopenshell.file,
    *,
    start: Sequence[float],
    direction: Sequence[float],
    length: float,
    radius: float,
    segments: int = 10,
) -> ifcopenshell.entity_instance:
    """Round bar (rebar) as a circular profile extruded along ``direction``."""
    dx, dy, dz = (float(v) for v in direction)
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    dx, dy, dz = dx / norm, dy / norm, dz / norm
    ref = (0.0, 0.0, 1.0) if abs(dz) < 0.9 else (1.0, 0.0, 0.0)
    circle = [
        (radius * math.cos(2.0 * math.pi * i / segments), radius * math.sin(2.0 * math.pi * i / segments))
        for i in range(segments)
    ]
    return extrude_profile(
        ifc_file, circle, length, origin=start, axis=(dx, dy, dz), ref_direction=ref
    )


def add_solid_product(
    core_or_file: StructuralCore | ifcopenshell.file,
    *,
    ifc_class: str,
    name: str,
    solids: ifcopenshell.entity_instance | Sequence[ifcopenshell.entity_instance],
    predefined_type: str | None = None,
    storey: ifcopenshell.entity_instance | None = None,
    body_context: ifcopenshell.entity_instance | None = None,
) -> ifcopenshell.entity_instance:
    """Storey-contained product at the world origin with world-coordinate solids."""
    if isinstance(core_or_file, StructuralCore):
        ifc_file = core_or_file.ifc_file
        storey = storey or core_or_file.storey
        body_context = body_context or core_or_file.body_context
    else:
        ifc_file = core_or_file
    if storey is None or body_context is None:
        raise ValueError("storey and body_context are required")
    product = create_entity(
        ifc_file, ifc_class=ifc_class, name=name, predefined_type=predefined_type
    )
    assign_container(ifc_file, relating_structure=storey, products=[product])
    edit_object_placement(ifc_file, product=product, matrix=translation_matrix())
    representation = create_body_representation(ifc_file, body_context, solids)
    assign_representation(ifc_file, product=product, representation=representation)
    return product


def add_void(
    core: StructuralCore,
    *,
    host: ifcopenshell.entity_instance,
    name: str,
    polyline: Sequence[Sequence[float]],
    z_bottom: float,
    height: float,
    predefined_type: str = "OPENING",
) -> ifcopenshell.entity_instance:
    """IfcOpeningElement voiding ``host``; plan polygon extruded from ``z_bottom``."""
    ifc_file = core.ifc_file
    opening = create_entity(
        ifc_file, ifc_class="IfcOpeningElement", name=name, predefined_type=predefined_type
    )
    edit_object_placement(ifc_file, product=opening, matrix=translation_matrix())
    solid = create_extruded_area_solid(
        ifc_file,
        [(float(p[0]), float(p[1])) for p in polyline],
        float(height),
        origin=(0.0, 0.0, float(z_bottom)),
    )
    representation = create_body_representation(ifc_file, core.body_context, solid)
    assign_representation(ifc_file, product=opening, representation=representation)
    add_feature(ifc_file, feature=opening, element=host)
    return opening


def add_wall_void(
    core: StructuralCore,
    *,
    host: ifcopenshell.entity_instance,
    name: str,
    x0: float,
    x1: float,
    z_bottom: float,
    height: float,
    y0: float | None = None,
    y1: float | None = None,
    predefined_type: str = "OPENING",
) -> ifcopenshell.entity_instance:
    """Void in the back wall (Y = 0 … wall thickness); oversized 1 cm through faces."""
    y0 = -0.01 if y0 is None else y0
    y1 = core.wall_thickness + 0.01 if y1 is None else y1
    return add_void(
        core,
        host=host,
        name=name,
        polyline=rect_polyline(x0, y0, x1, y1),
        z_bottom=z_bottom,
        height=height,
        predefined_type=predefined_type,
    )


def add_round_wall_void(
    core: StructuralCore,
    *,
    host: ifcopenshell.entity_instance,
    name: str,
    x: float,
    z: float,
    radius: float,
    segments: int = 32,
) -> ifcopenshell.entity_instance:
    """Round through-void (core drilling) across the back wall, centred at (x, z)."""
    ifc_file = core.ifc_file
    opening = create_entity(
        ifc_file, ifc_class="IfcOpeningElement", name=name, predefined_type="OPENING"
    )
    edit_object_placement(ifc_file, product=opening, matrix=translation_matrix())
    solid = bar_solid(
        ifc_file,
        start=(float(x), -0.01, float(z)),
        direction=(0.0, 1.0, 0.0),
        length=core.wall_thickness + 0.02,
        radius=float(radius),
        segments=segments,
    )
    representation = create_body_representation(ifc_file, core.body_context, solid)
    assign_representation(ifc_file, product=opening, representation=representation)
    add_feature(ifc_file, feature=opening, element=host)
    return opening


def add_bearing_pad(
    core: StructuralCore,
    *,
    name: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    z_bottom: float,
    thickness: float = BEARING_PAD_THICKNESS,
) -> ifcopenshell.entity_instance:
    """Flexible elastomer bearing pad (context; rendered dark grey)."""
    pad = add_solid_product(
        core,
        ifc_class="IfcDiscreteAccessory",
        name=name,
        solids=box_solid(core.ifc_file, x0, y0, x1, y1, z_bottom, z_bottom + thickness),
        predefined_type="USERDEFINED",
    )
    pad.ObjectType = BEARING_PAD_OBJECT_TYPE
    return pad


def apply_attributes(
    ifc_file: ifcopenshell.file,
    product: ifcopenshell.entity_instance,
    attrs: dict[str, Any] | None,
    **overrides: Any,
) -> None:
    """Write YAML-resolved entity fields, psets and qtos onto ``product``.

    ``overrides`` replace entity fields (``Name=…``) or whole qto values
    (``quantities={...}``) for this product.
    """
    attrs = dict(attrs or {})
    quantities = overrides.pop("quantities", None)
    properties = overrides.pop("properties", None)
    merged = {**attrs, **overrides}
    for key in _ENTITY_FIELD_MAP:
        if key in merged and merged[key] is not None and hasattr(product, key):
            setattr(product, key, merged[key])
    datatypes = attrs.get("property_datatypes") or {}
    psets = {k: dict(v) for k, v in (attrs.get("properties") or {}).items()}
    for pset_name, values in (properties or {}).items():
        psets.setdefault(pset_name, {}).update(values)
    for pset_name, values in psets.items():
        assign_pset(ifc_file, product, pset_name, values, datatypes=datatypes.get(pset_name))
    qtos = {k: dict(v) for k, v in (attrs.get("quantities") or {}).items()}
    for qto_name, values in (quantities or {}).items():
        qtos.setdefault(qto_name, {}).update(values)
    for qto_name, values in qtos.items():
        assign_qto(ifc_file, product, qto_name, values)


def build_structural_core(params: dict[str, Any] | None = None) -> StructuralCore:
    """Build the shared structural vignette.

    ``params`` keys (all optional):
    - ``project_name``
    - ``slab_width`` / ``slab_depth`` / ``base_thickness``
    - ``include_base_slab`` (default True)
    - ``wall``: ``"base"`` (on the base slab, default), ``"floor"`` (on top of
      the floor slab, upper storey) or ``None``
    - ``wall_span``: ``(x0, x1)`` along the back edge; ``wall_height`` (storey
      height) / ``wall_thickness``; ``upper_wall_height`` for ``wall="floor"``
    - ``build_wall`` (default True): False keeps the wall levels on ``core``
      but lets the card build its own wall body
    - ``include_column`` (default True), ``column_center``, ``column_size``
    - ``floor_slab``: ``"full"``, ``"l_cut"`` (front quadrant removed through
      the column centre) or ``None`` (default)
    - ``floor_span``: ``(x0, y0, x1, y1)`` footprint of the floor slab
      (default: full base slab)
    """
    params = dict(params or {})
    slab_w = float(params.get("slab_width", DEFAULT_SLAB_WIDTH))
    slab_d = float(params.get("slab_depth", DEFAULT_SLAB_DEPTH))
    base_t = float(params.get("base_thickness", BASE_SLAB_THICKNESS))
    wall_t = float(params.get("wall_thickness", WALL_THICKNESS))
    wall_h = float(params.get("wall_height", WALL_HEIGHT))
    col = float(params.get("column_size", COLUMN_SIZE))
    floor_t = float(params.get("floor_thickness", FLOOR_SLAB_THICKNESS))
    cx, cy = (float(v) for v in params.get("column_center", DEFAULT_COLUMN_CENTER))
    wall_mode = params.get("wall", "base")
    floor_mode = params.get("floor_slab")
    if wall_mode not in {"base", "floor", None}:
        raise ValueError(f"unsupported wall mode: {wall_mode!r}")
    if floor_mode not in {"full", "l_cut", None}:
        raise ValueError(f"unsupported floor_slab mode: {floor_mode!r}")
    if wall_mode == "floor" and floor_mode is None:
        raise ValueError("wall='floor' requires a floor slab")

    ifc_file, _project, _site, _building, storey, body_context = create_project_shell(
        str(params.get("project_name") or "Tragwerk"), storey_name="EG"
    )
    body_context = get_body_context(ifc_file) or body_context
    core = StructuralCore(
        ifc_file=ifc_file,
        storey=storey,
        body_context=body_context,
        slab_width=slab_w,
        slab_depth=slab_d,
        base_thickness=base_t,
        wall_thickness=wall_t,
        storey_height=wall_h,
        column_size=col,
        column_center=(cx, cy),
        floor_thickness=floor_t,
    )

    if params.get("include_base_slab", True):
        core.base_slab = add_solid_product(
            core,
            ifc_class="IfcSlab",
            name="Bodenplatte",
            solids=box_solid(ifc_file, 0.0, 0.0, slab_w, slab_d, 0.0, base_t),
            predefined_type="BASESLAB",
        )

    fx0, fy0, fx1, fy1 = (
        float(v) for v in params.get("floor_span", (0.0, 0.0, slab_w, slab_d))
    )
    if floor_mode is not None:
        z0 = core.floor_bottom
        if floor_mode == "full":
            poly = rect_polyline(fx0, fy0, fx1, fy1)
        else:
            poly = [
                (fx0, fy0),
                (fx1, fy0),
                (fx1, cy),
                (cx, cy),
                (cx, fy1),
                (fx0, fy1),
            ]
        core.floor_slab = add_solid_product(
            core,
            ifc_class="IfcSlab",
            name="D-01",
            solids=create_extruded_area_solid(ifc_file, poly, floor_t, origin=(0.0, 0.0, z0)),
            predefined_type="FLOOR",
        )

    if wall_mode is not None:
        wx0, wx1 = (float(v) for v in params.get("wall_span", (0.0, slab_w)))
        if wall_mode == "base":
            core.wall_bottom = base_t
            core.wall_body_height = wall_h
        else:
            core.wall_bottom = core.floor_top
            core.wall_body_height = float(params.get("upper_wall_height", wall_h))
        core.wall_span = (wx0, wx1)
        if params.get("build_wall", True):
            core.wall = add_solid_product(
                core,
                ifc_class="IfcWall",
                name="W-01",
                solids=box_solid(ifc_file, wx0, 0.0, wx1, wall_t, core.wall_bottom, core.wall_top),
                predefined_type="SOLIDWALL",
            )

    if params.get("include_column", True):
        z_top = core.floor_bottom if floor_mode is not None else base_t + wall_h
        core.column = add_solid_product(
            core,
            ifc_class="IfcColumn",
            name="S-01",
            solids=box_solid(
                ifc_file, cx - col / 2, cy - col / 2, cx + col / 2, cy + col / 2, base_t, z_top
            ),
            predefined_type="COLUMN",
        )

    return core
