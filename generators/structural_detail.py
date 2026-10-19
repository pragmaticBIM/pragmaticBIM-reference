"""Structural "detailliert" catalog cards on the shared shell-construction vignette.

One builder per card (column, wall, slabs, footing, stair, ramp, rebar, edge
strip). Each returns ``(ifc_file, primaries, dotted)``: the accented products
and the context products drawn as dashed outlines.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

import ifcopenshell

from generators.parts import create_extruded_area_solid, rect_polyline
from generators.structural_core import (
    BEARING_PAD_THICKNESS,
    StructuralCore,
    add_bearing_pad,
    add_round_wall_void,
    add_solid_product,
    add_void,
    add_wall_void,
    apply_attributes,
    bar_solid,
    box_solid,
    build_structural_core,
    extrude_with_voids,
    extrude_yz_along_x,
)

# (ifc_file, primaries, dotted[, thin_edge])
CardResult = tuple[Any, ...]


def _shoelace(points: Sequence[Sequence[float]]) -> float:
    area = 0.0
    for i, (x0, y0) in enumerate(points):
        x1, y1 = points[(i + 1) % len(points)]
        area += x0 * y1 - x1 * y0
    return abs(area) * 0.5


def _core(params: dict[str, Any], **overrides: Any) -> StructuralCore:
    return build_structural_core(
        {"project_name": params.get("project_name") or "Tragwerk", **overrides}
    )


def _gross_volume(qto_name: str, volume: float) -> dict[str, dict[str, float]]:
    return {qto_name: {"GrossVolume": round(volume, 3)}}


# --- Stütze detailliert ------------------------------------------------------

COLUMN_CHAMFER = 0.04
COLUMN_HEAD_SIZE = 0.90
COLUMN_HEAD_DEPTH = 0.20


def _column(params: dict[str, Any]) -> CardResult:
    """Chamfered column with a head strengthening under an L-cut floor slab."""
    core = _core(
        params,
        wall="base",
        include_column=False,
        column_center=(2.0, 2.0),
        floor_slab="l_cut",
    )
    ifc_file = core.ifc_file
    cx, cy = core.column_center
    s = float(params.get("column_size", core.column_size))
    c = float(params.get("column_chamfer", COLUMN_CHAMFER))
    head = float(params.get("head_size", COLUMN_HEAD_SIZE))
    head_d = float(params.get("head_depth", COLUMN_HEAD_DEPTH))
    x0, y0, x1, y1 = cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2
    octagon = [
        (x0 + c, y0),
        (x1 - c, y0),
        (x1, y0 + c),
        (x1, y1 - c),
        (x1 - c, y1),
        (x0 + c, y1),
        (x0, y1 - c),
        (x0, y0 + c),
    ]
    shaft_h = core.floor_bottom - head_d - core.base_top
    solids = [
        create_extruded_area_solid(ifc_file, octagon, shaft_h, origin=(0.0, 0.0, core.base_top)),
        box_solid(
            ifc_file,
            cx - head / 2,
            cy - head / 2,
            cx + head / 2,
            cy + head / 2,
            core.floor_bottom - head_d,
            core.floor_bottom,
        ),
    ]
    column = add_solid_product(
        core, ifc_class="IfcColumn", name="S-01", solids=solids, predefined_type="COLUMN"
    )
    volume = _shoelace(octagon) * shaft_h + head * head * head_d
    apply_attributes(
        ifc_file,
        column,
        params.get("attrs"),
        quantities=_gross_volume("Qto_ColumnBaseQuantities", volume),
    )
    return ifc_file, [column], []


# --- Wand detailliert --------------------------------------------------------

DOOR_SPAN = (0.6, 1.6)
DOOR_HEIGHT = 2.10
RECESS_SPAN = (2.5, 3.2)
RECESS_Z = (1.60, 2.10)
RECESS_DEPTH = 0.10
CORE_DRILL_X = (2.05, 2.85, 3.65)
CORE_DRILL_BELOW_TOP = 0.25
CORE_DRILL_RADIUS = 0.08


def _wall(params: dict[str, Any]) -> CardResult:
    """Wall with door opening, recess and round core drillings near the top."""
    core = _core(params, wall="base", build_wall=False, include_column=False, floor_slab=None)
    ifc_file = core.ifc_file
    t = core.wall_thickness
    zb, zt = core.wall_bottom, core.wall_top
    x0, x1 = core.wall_span
    wall = add_solid_product(
        core,
        ifc_class="IfcWall",
        name="W-01",
        solids=box_solid(ifc_file, x0, 0.0, x1, t, zb, zt),
        predefined_type="SOLIDWALL",
    )
    add_wall_void(
        core,
        host=wall,
        name="TÜ-01",
        x0=DOOR_SPAN[0],
        x1=DOOR_SPAN[1],
        z_bottom=zb - 0.01,
        height=DOOR_HEIGHT + 0.01,
    )
    add_wall_void(
        core,
        host=wall,
        name="AS-01",
        x0=RECESS_SPAN[0],
        x1=RECESS_SPAN[1],
        z_bottom=zb + RECESS_Z[0],
        height=RECESS_Z[1] - RECESS_Z[0],
        y0=t - RECESS_DEPTH,
        predefined_type="RECESS",
    )
    for index, x in enumerate(CORE_DRILL_X):
        add_round_wall_void(
            core,
            host=wall,
            name=f"KB-{index + 1:02d}",
            x=x,
            z=zt - CORE_DRILL_BELOW_TOP,
            radius=CORE_DRILL_RADIUS,
        )
    apply_attributes(ifc_file, wall, params.get("attrs"))
    return ifc_file, [wall], []


# --- Decke detailliert -------------------------------------------------------

SHAFT_RECT = (0.5, 1.4, 1.5, 2.2)
WET_ROOM_RECT = (0.6, 2.6, 2.2, 3.6)
WET_ROOM_DEPTH = 0.06


def _slab_floor(params: dict[str, Any]) -> CardResult:
    """Floor slab with a shaft opening and a stepped wet-room recess."""
    core = _core(params, wall="base", column_center=(2.9, 1.5), floor_slab="full")
    ifc_file = core.ifc_file
    slab = core.floor_slab
    add_void(
        core,
        host=slab,
        name="SCH-01",
        polyline=rect_polyline(*SHAFT_RECT),
        z_bottom=core.floor_bottom - 0.01,
        height=core.floor_thickness + 0.02,
    )
    add_void(
        core,
        host=slab,
        name="ABS-01",
        polyline=rect_polyline(*WET_ROOM_RECT),
        z_bottom=core.floor_top - WET_ROOM_DEPTH,
        height=WET_ROOM_DEPTH + 0.01,
        predefined_type="RECESS",
    )
    volume = (
        core.slab_width * core.slab_depth * core.floor_thickness
        - _shoelace(rect_polyline(*SHAFT_RECT)) * core.floor_thickness
        - _shoelace(rect_polyline(*WET_ROOM_RECT)) * WET_ROOM_DEPTH
    )
    apply_attributes(
        ifc_file, slab, params.get("attrs"), quantities=_gross_volume("Qto_SlabBaseQuantities", volume)
    )
    return ifc_file, [slab], []


# --- Bodenplatte detailliert -------------------------------------------------

PIT_RECT = (0.7, 1.4, 2.3, 3.0)
# Keeps the slab AABB plate-like so the renderer still engraves its top
PIT_DEPTH = 1.00
PIT_WALL = 0.25
PIT_FLOOR = 0.30
EDGE_BEAM_WIDTH = 0.50
EDGE_BEAM_DEPTH = 0.40
SUMP_RECT = (2.8, 2.3, 3.3, 2.8)
SUMP_DEPTH = 0.20


def _slab_base(params: dict[str, Any]) -> CardResult:
    """Base slab with lift pit, sump and thickened edge along the visible edges."""
    core = _core(
        params,
        include_base_slab=False,
        wall="base",
        wall_height=1.20,
        column_center=(3.0, 1.2),
        floor_slab=None,
    )
    ifc_file = core.ifc_file
    w, d, t = core.slab_width, core.slab_depth, core.base_thickness
    px0, py0, px1, py1 = PIT_RECT
    pit = rect_polyline(px0, py0, px1, py1)
    pit_outer = rect_polyline(px0 - PIT_WALL, py0 - PIT_WALL, px1 + PIT_WALL, py1 + PIT_WALL)
    z_pit_floor = t - PIT_DEPTH
    edge = [
        (w - EDGE_BEAM_WIDTH, 0.0),
        (w, 0.0),
        (w, d),
        (0.0, d),
        (0.0, d - EDGE_BEAM_WIDTH),
        (w - EDGE_BEAM_WIDTH, d - EDGE_BEAM_WIDTH),
    ]
    solids = [
        extrude_with_voids(ifc_file, rect_polyline(0.0, 0.0, w, d), [pit], t),
        extrude_with_voids(ifc_file, pit_outer, [pit], -z_pit_floor, z_bottom=z_pit_floor),
        create_extruded_area_solid(
            ifc_file, pit_outer, PIT_FLOOR, origin=(0.0, 0.0, z_pit_floor - PIT_FLOOR)
        ),
        create_extruded_area_solid(
            ifc_file, edge, EDGE_BEAM_DEPTH, origin=(0.0, 0.0, -EDGE_BEAM_DEPTH)
        ),
    ]
    slab = add_solid_product(
        core, ifc_class="IfcSlab", name="BP-01", solids=solids, predefined_type="BASESLAB"
    )
    add_void(
        core,
        host=slab,
        name="PS-01",
        polyline=rect_polyline(*SUMP_RECT),
        z_bottom=t - SUMP_DEPTH,
        height=SUMP_DEPTH + 0.01,
        predefined_type="RECESS",
    )
    pit_area, ring_area = _shoelace(pit), _shoelace(pit_outer) - _shoelace(pit)
    volume = (
        (w * d - pit_area) * t
        + ring_area * -z_pit_floor
        + _shoelace(pit_outer) * PIT_FLOOR
        + _shoelace(edge) * EDGE_BEAM_DEPTH
        - _shoelace(rect_polyline(*SUMP_RECT)) * SUMP_DEPTH
    )
    apply_attributes(
        ifc_file, slab, params.get("attrs"), quantities=_gross_volume("Qto_SlabBaseQuantities", volume)
    )
    return ifc_file, [slab], []


# --- Flachdach detailliert ---------------------------------------------------

ROOF_SPAN = 4.0
UPSTAND_WIDTH = 0.20
UPSTAND_HEIGHT = 0.30
ROOF_HATCH_RECT = (1.0, 1.2, 1.9, 2.1)


def _slab_roof(params: dict[str, Any]) -> CardResult:
    """Roof slab with a cast-in upstand and a roof hatch opening.

    The base slab runs past the roof on the camera side so the brand has a
    visible white plate.
    """
    core = _core(
        params,
        slab_width=ROOF_SPAN + 1.2,
        slab_depth=ROOF_SPAN + 1.2,
        wall="base",
        wall_span=(0.0, ROOF_SPAN),
        column_center=(2.8, 2.8),
        floor_slab=None,
    )
    ifc_file = core.ifc_file
    z0, z1 = core.floor_bottom, core.floor_top
    outer = rect_polyline(0.0, 0.0, ROOF_SPAN, ROOF_SPAN)
    inner = rect_polyline(
        UPSTAND_WIDTH, UPSTAND_WIDTH, ROOF_SPAN - UPSTAND_WIDTH, ROOF_SPAN - UPSTAND_WIDTH
    )
    solids = [
        create_extruded_area_solid(ifc_file, outer, core.floor_thickness, origin=(0.0, 0.0, z0)),
        extrude_with_voids(ifc_file, outer, [inner], UPSTAND_HEIGHT, z_bottom=z1),
    ]
    roof = add_solid_product(
        core, ifc_class="IfcSlab", name="FD-01", solids=solids, predefined_type="ROOF"
    )
    add_void(
        core,
        host=roof,
        name="DA-01",
        polyline=rect_polyline(*ROOF_HATCH_RECT),
        z_bottom=z0 - 0.01,
        height=core.floor_thickness + 0.02,
    )
    volume = (
        (_shoelace(outer) - _shoelace(rect_polyline(*ROOF_HATCH_RECT))) * core.floor_thickness
        + (_shoelace(outer) - _shoelace(inner)) * UPSTAND_HEIGHT
    )
    apply_attributes(
        ifc_file, roof, params.get("attrs"), quantities=_gross_volume("Qto_SlabBaseQuantities", volume)
    )
    return ifc_file, [roof], []


# --- Fundament detailliert ---------------------------------------------------

STRIP_WIDTH = 0.80
STRIP_DEPTH = 0.40
PAD_SIZE = 1.40
PAD_DEPTH = 0.50
BLINDING_THICKNESS = 0.05
BLINDING_MARGIN = 0.10


def _footing(params: dict[str, Any]) -> CardResult:
    """Strip footing under the wall and pad footing under the column.

    The base slab is drawn as a dashed outline so both footings stay visible;
    a thin blinding layer (Magerbeton) sits under each footing.
    """
    core = _core(
        params,
        include_base_slab=False,
        wall="base",
        wall_height=1.20,
        floor_slab=None,
    )
    ifc_file = core.ifc_file
    w, d, t = core.slab_width, core.slab_depth, core.base_thickness
    base = add_solid_product(
        core,
        ifc_class="IfcSlab",
        name="Bodenplatte",
        solids=box_solid(ifc_file, 0.0, 0.0, w, d, 0.0, t),
        predefined_type="BASESLAB",
    )
    wy = core.wall_thickness / 2
    strip_rect = (0.0, wy - STRIP_WIDTH / 2, w, wy + STRIP_WIDTH / 2)
    cx, cy = core.column_center
    pad_rect = (cx - PAD_SIZE / 2, cy - PAD_SIZE / 2, cx + PAD_SIZE / 2, cy + PAD_SIZE / 2)
    strip = add_solid_product(
        core,
        ifc_class="IfcFooting",
        name="F-01",
        solids=box_solid(ifc_file, *strip_rect, -STRIP_DEPTH, 0.0),
        predefined_type="STRIP_FOOTING",
    )
    pad = add_solid_product(
        core,
        ifc_class="IfcFooting",
        name="F-02",
        solids=box_solid(ifc_file, *pad_rect, -PAD_DEPTH, 0.0),
        predefined_type="PAD_FOOTING",
    )
    for rect, z_top, label in ((strip_rect, -STRIP_DEPTH, "01"), (pad_rect, -PAD_DEPTH, "02")):
        m = BLINDING_MARGIN
        blinding = add_solid_product(
            core,
            ifc_class="IfcBuildingElementProxy",
            name=f"MB-{label}",
            solids=box_solid(
                ifc_file,
                rect[0] - m,
                rect[1] - m,
                rect[2] + m,
                rect[3] + m,
                z_top - BLINDING_THICKNESS,
                z_top,
            ),
            predefined_type="USERDEFINED",
        )
        blinding.ObjectType = "Magerbeton"
    attrs = params.get("attrs")
    apply_attributes(
        ifc_file,
        strip,
        attrs,
        quantities=_gross_volume(
            "Qto_FootingBaseQuantities", _shoelace(rect_polyline(*strip_rect)) * STRIP_DEPTH
        ),
    )
    apply_attributes(
        ifc_file,
        pad,
        attrs,
        Name="F-02",
        PredefinedType="PAD_FOOTING",
        quantities=_gross_volume("Qto_FootingBaseQuantities", PAD_SIZE * PAD_SIZE * PAD_DEPTH),
    )
    return ifc_file, [strip, pad], [base]


# --- Treppe detailliert ------------------------------------------------------

STAIR_RISERS = 10
STAIR_GOING = 0.28
STAIR_WAIST = 0.16
STAIR_WIDTH = 1.20
LANDING_DEPTH = 1.40
LANDING_SPAN = (0.8, 3.2)
STAIR_X0 = LANDING_SPAN[0]
LANDING_TOP = 2.05
LEDGE_DEPTH = 0.16
LEDGE_HEIGHT = 0.20
FLIGHT_TOP_THICKNESS = 0.20
FLIGHT_TOP_LENGTH = 0.50
STAIR_GAP = 0.01


def _stair(params: dict[str, Any]) -> CardResult:
    """Precast flight on elastomer pads: base slab at the foot, landing ledge at the top."""
    base_t = 0.30
    z_ledge = LANDING_TOP - FLIGHT_TOP_THICKNESS - BEARING_PAD_THICKNESS
    landing_bottom = z_ledge - LEDGE_HEIGHT
    core = _core(
        params,
        slab_depth=4.9,
        wall="base",
        wall_span=LANDING_SPAN,
        wall_height=landing_bottom - base_t,
        include_column=False,
        floor_slab=None,
    )
    ifc_file = core.ifc_file
    pad_t = BEARING_PAD_THICKNESS
    yf = LANDING_DEPTH
    zt = LANDING_TOP
    landing_profile = [
        (0.0, zt),
        (yf, zt),
        (yf, z_ledge),
        (yf + LEDGE_DEPTH, z_ledge),
        (yf + LEDGE_DEPTH, landing_bottom),
        (0.0, landing_bottom),
    ]
    lx0, lx1 = LANDING_SPAN
    add_solid_product(
        core,
        ifc_class="IfcSlab",
        name="Podest",
        solids=extrude_yz_along_x(ifc_file, landing_profile, x0=lx0, length=lx1 - lx0),
        predefined_type="LANDING",
    )

    n, g = STAIR_RISERS, STAIR_GOING
    z_b = core.base_top + pad_t
    r = (zt - z_b) / n
    slope = r / g
    waist_v = STAIR_WAIST / math.cos(math.atan(slope))
    top_bottom = n * r - FLIGHT_TOP_THICKNESS
    u_end = (n - 1) * g + FLIGHT_TOP_LENGTH
    u_soffit_top = (top_bottom + waist_v) / slope
    u_soffit_foot = waist_v / slope
    if u_soffit_top > u_end - LEDGE_DEPTH:
        raise ValueError("flight top segment too short to bear on the landing ledge")
    # Flight profile in (u, z): u runs from the bottom riser towards the landing
    profile_uz: list[tuple[float, float]] = [(0.0, 0.0)]
    for k in range(n):
        profile_uz.append((k * g, (k + 1) * r))
        profile_uz.append(((k + 1) * g if k < n - 1 else u_end, (k + 1) * r))
    profile_uz += [(u_end, top_bottom), (u_soffit_top, top_bottom), (u_soffit_foot, 0.0)]
    y0 = yf + STAIR_GAP + u_end
    profile_yz = [(y0 - u, z_b + z) for u, z in profile_uz]
    flight = add_solid_product(
        core,
        ifc_class="IfcStair",
        name="TR-01",
        solids=extrude_yz_along_x(ifc_file, profile_yz, x0=STAIR_X0, length=STAIR_WIDTH),
        predefined_type="STRAIGHT_RUN_STAIR",
    )

    px0, px1 = STAIR_X0 + 0.02, STAIR_X0 + STAIR_WIDTH - 0.02
    add_bearing_pad(
        core,
        name="EL-01",
        x0=px0,
        x1=px1,
        y0=y0 - u_soffit_foot + 0.02,
        y1=y0 - 0.02,
        z_bottom=core.base_top,
    )
    add_bearing_pad(
        core,
        name="EL-02",
        x0=px0,
        x1=px1,
        y0=yf + STAIR_GAP + 0.01,
        y1=yf + LEDGE_DEPTH - 0.01,
        z_bottom=z_ledge,
    )
    apply_attributes(ifc_file, flight, params.get("attrs"))
    return ifc_file, [flight], []


# --- Rampe detailliert -------------------------------------------------------

RAMP_RISE = 0.80
RAMP_RUN = 4.40
RAMP_THICKNESS = 0.25
RAMP_SPAN = (0.3, 3.7)
UPPER_DEPTH = 1.20
BACK_WALL_ABOVE = 1.20
CHANNEL_SLOT = (0.30, 0.20)  # width (Y), depth (Z)


def _ramp(params: dict[str, Any]) -> CardResult:
    """Sloped ramp slab with a slot (Schlitz) for a drainage channel at the foot.

    The upper level spans from the back wall, which rises above it, to a
    support wall under its front edge; ramp and slot share the same width.
    """
    base_t = 0.30
    upper_top = base_t + RAMP_RISE
    upper_bottom = upper_top - RAMP_THICKNESS
    core = _core(
        params,
        slab_depth=7.2,
        wall="base",
        wall_height=upper_top - base_t + BACK_WALL_ABOVE,
        include_column=False,
        floor_slab=None,
    )
    ifc_file = core.ifc_file
    w = core.slab_width
    add_solid_product(
        core,
        ifc_class="IfcSlab",
        name="Oberes Niveau",
        solids=box_solid(
            ifc_file, 0.0, core.wall_thickness, w, UPPER_DEPTH, upper_bottom, upper_top
        ),
        predefined_type="FLOOR",
    )
    add_solid_product(
        core,
        ifc_class="IfcWall",
        name="W-02",
        solids=box_solid(
            ifc_file, 0.0, UPPER_DEPTH - core.wall_thickness, w, UPPER_DEPTH, base_t, upper_bottom
        ),
        predefined_type="SOLIDWALL",
    )

    y_top, y_foot = UPPER_DEPTH, UPPER_DEPTH + RAMP_RUN
    y_soffit = y_foot - RAMP_THICKNESS * RAMP_RUN / RAMP_RISE
    profile = [
        (y_top, upper_top),
        (y_foot, base_t),
        (y_soffit, base_t),
        (y_top, upper_bottom),
    ]
    rx0, rx1 = RAMP_SPAN
    ramp = add_solid_product(
        core,
        ifc_class="IfcRamp",
        name="RA-01",
        solids=extrude_yz_along_x(ifc_file, profile, x0=rx0, length=rx1 - rx0),
        predefined_type="STRAIGHT_RUN_RAMP",
    )

    slot_w, slot_d = CHANNEL_SLOT
    sx0, sx1 = rx0, rx1
    sy0 = y_foot + 0.02
    add_void(
        core,
        host=core.base_slab,
        name="SL-01",
        polyline=rect_polyline(sx0, sy0, sx1, sy0 + slot_w),
        z_bottom=base_t - slot_d,
        height=slot_d + 0.01,
        predefined_type="RECESS",
    )
    add_solid_product(
        core,
        ifc_class="IfcPipeSegment",
        name="Rinne",
        solids=box_solid(
            ifc_file, sx0, sy0 + 0.03, sx1, sy0 + slot_w - 0.03, base_t - slot_d + 0.02, base_t
        ),
        predefined_type="GUTTER",
    )
    apply_attributes(ifc_file, ramp, params.get("attrs"))
    return ifc_file, [ramp], []


# --- Bewehrung ---------------------------------------------------------------

REBAR_SLAB = 2.40
# White base slab extends past the dashed slab corner and carries the brand
REBAR_BASE_MARGIN = 0.90
REBAR_SPACING = 0.30
REBAR_COVER = 0.03
# Drawn thicker than Ø16 so bars read at catalog size
REBAR_DRAW_RADIUS = 0.016
# Facets under the renderer's 15° crease angle: no stroke along each facet
REBAR_SEGMENTS = 32


def _rebar(params: dict[str, Any]) -> CardResult:
    """Slab corner (dashed) with two orange rebar layers, each in both directions."""
    size = float(params.get("slab_size", REBAR_SLAB))
    core = _core(
        params,
        slab_width=size + REBAR_BASE_MARGIN,
        slab_depth=size + REBAR_BASE_MARGIN,
        wall="base",
        wall_span=(0.0, size),
        wall_height=1.20,
        floor_slab="full",
        floor_span=(0.0, 0.0, size, size),
        include_column=False,
    )
    ifc_file = core.ifc_file
    spacing = float(params.get("bar_spacing", REBAR_SPACING))
    r = REBAR_DRAW_RADIUS
    c = REBAR_COVER
    positions = []
    p = spacing / 2
    while p < size:
        positions.append(p)
        p += spacing
    length = size - 2 * c
    layers = [
        ("1", "x", core.floor_bottom + c + r),
        ("2", "y", core.floor_bottom + c + 3 * r),
        ("3", "x", core.floor_top - c - r),
        ("4", "y", core.floor_top - c - 3 * r),
    ]
    attrs = params.get("attrs") or {}
    allplan = (attrs.get("properties") or {}).get("AllplanAttributes") or {}
    diameter = float(allplan.get("Bewehrungsdurchmesser", 16)) / 1000.0
    bars: list[ifcopenshell.entity_instance] = []
    for position, axis, z in layers:
        for index, q in enumerate(positions):
            if axis == "x":
                start, direction = (c, q, z), (1.0, 0.0, 0.0)
            else:
                start, direction = (q, c, z), (0.0, 1.0, 0.0)
            bar = add_solid_product(
                core,
                ifc_class="IfcReinforcingBar",
                name=f"Pos {position}.{index + 1:02d}",
                solids=bar_solid(
                    ifc_file,
                    start=start,
                    direction=direction,
                    length=length,
                    radius=r,
                    segments=REBAR_SEGMENTS,
                ),
                predefined_type="MAIN",
            )
            bar.NominalDiameter = diameter
            bar.BarLength = length
            apply_attributes(
                ifc_file,
                bar,
                attrs,
                properties={
                    "AllplanAttributes": {
                        "Bewehrungsposition": position,
                        "Stückzahl": str(len(positions)),
                    }
                },
            )
            bars.append(bar)
    return ifc_file, bars, [core.floor_slab], bars


# --- Randstreifen ------------------------------------------------------------

EDGE_STRIP_THICKNESS = 0.05


def _edge_strip(params: dict[str, Any]) -> CardResult:
    """Orange edge formwork along the two camera-facing floor-slab edges."""
    core = _core(params, wall="base", floor_slab="full")
    ifc_file = core.ifc_file
    w, d = core.slab_width, core.slab_depth
    s = float(params.get("strip_thickness", EDGE_STRIP_THICKNESS))
    footprint = [(0.0, d), (w, d), (w, 0.0), (w + s, 0.0), (w + s, d + s), (0.0, d + s)]
    strip = add_solid_product(
        core,
        ifc_class="IfcBuildingElementProxy",
        name="RS-01",
        solids=create_extruded_area_solid(
            ifc_file, footprint, core.floor_thickness, origin=(0.0, 0.0, core.floor_bottom)
        ),
        predefined_type="USERDEFINED",
    )
    apply_attributes(ifc_file, strip, params.get("attrs"), Name="RS-01")
    return ifc_file, [strip], []


_CARDS: dict[str, Callable[[dict[str, Any]], CardResult]] = {
    "column": _column,
    "wall": _wall,
    "slab_floor": _slab_floor,
    "slab_base": _slab_base,
    "slab_roof": _slab_roof,
    "footing": _footing,
    "stair": _stair,
    "ramp": _ramp,
    "rebar": _rebar,
    "edge_strip": _edge_strip,
}


def generate_structural_detail(params: dict[str, Any]) -> CardResult:
    """Build the structural card named by ``params['card']``."""
    card = str(params.get("card") or "")
    try:
        builder = _CARDS[card]
    except KeyError as exc:
        raise ValueError(f"unknown structural card: {card!r}") from exc
    return builder(params)
