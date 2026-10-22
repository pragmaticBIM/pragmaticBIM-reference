"""MEP riser (Steigzone) on the spatial-structure slab stack."""

from __future__ import annotations

import math
from typing import Any

import ifcopenshell

from generators.base import get_body_context
from generators.mep_parts import MepScene, box_solid, duct_solid, pipe_solid
from generators.parts import create_extruded_area_solid, rect_polyline
from generators.spatial_structure import (
    DEFAULT_SLAB_THICKNESS,
    DEFAULT_STOREY_SPACING,
    generate_spatial_structure,
)

# Metres. Plot 12 × 10 → building footprint x 2..10, y 2..8; balcony on 01
# at x 4..8, y 8..9.5. The riser sits in the front-right corner (nearest the
# camera); horizontal runs hang under the roof slab, which the segment cards
# draw dashed so the runs stay visible.
PLOT_WIDTH = 12.0
PLOT_DEPTH = 10.0
SLAB_T = DEFAULT_SLAB_THICKNESS
FLOOR_01 = DEFAULT_STOREY_SPACING
ROOF = 2.0 * DEFAULT_STOREY_SPACING
RISER_BOTTOM = SLAB_T
RISER_TOP = ROOF + SLAB_T + 0.35
RUN_END_X = 3.2
SOFFIT_GAP = 0.05

PIPE_R = 0.06
PIPE_VL = (8.75, 7.30)
PIPE_RL = (8.75, 7.55)
DUCT_CENTER = (9.25, 6.85)
DUCT_RISER = (0.40, 0.30)
DUCT_RUN = (0.30, 0.30)
TRAY_CENTER = (8.40, 6.34)
TRAY_RISER = (0.08, 0.40)
TRAY_RUN = (0.40, 0.08)
VOID_FOOTPRINT = (8.15, 6.10, 9.55, 7.75)
VOID_MARGIN = 0.05
DOWNPIPE_ROOF = (2.30, 7.65)
DOWNPIPE_BALCONY = (5.00, 9.30)
DOWNPIPE_R = 0.07

RISER_SLUGS = frozenset(
    {
        "mep-schematic-pipe",
        "mep-schematic-duct",
        "mep-schematic-tray",
        "mep-downpipe",
        "mep-provision-for-void",
    }
)
SEGMENT_SLUGS = frozenset(
    {"mep-schematic-pipe", "mep-schematic-duct", "mep-schematic-tray"}
)


def _pipe_run(
    f: ifcopenshell.file, xy: tuple[float, float], z_run: float, radius: float
) -> list[ifcopenshell.entity_instance]:
    x, y = xy
    return [
        pipe_solid(f, (x, y, RISER_BOTTOM), (x, y, RISER_TOP), radius),
        pipe_solid(f, (x, y, z_run), (RUN_END_X, y, z_run), radius),
    ]


def _void_box(
    f: ifcopenshell.file, footprint: tuple[float, float, float, float], slab_bottom: float
) -> ifcopenshell.entity_instance:
    x0, y0, x1, y1 = footprint
    return box_solid(
        f,
        x0,
        y0,
        slab_bottom - VOID_MARGIN,
        x1,
        y1,
        slab_bottom + SLAB_T + VOID_MARGIN,
    )


def _cut_slab_holes(
    f: ifcopenshell.file,
    slab: ifcopenshell.entity_instance,
    footprints: list[tuple[float, float, float, float]],
) -> None:
    """Boolean-subtract rectangular holes from a slab body (slab-local Z, world XY)."""
    representation = slab.Representation.Representations[0]
    item = representation.Items[0]
    for x0, y0, x1, y1 in footprints:
        cutter = create_extruded_area_solid(
            f,
            rect_polyline(x0, y0, x1, y1),
            SLAB_T + 0.02,
            origin=(0.0, 0.0, -0.01),
        )
        item = f.create_entity(
            "IfcBooleanResult",
            Operator="DIFFERENCE",
            FirstOperand=item,
            SecondOperand=cutter,
        )
    representation.Items = [item]
    representation.RepresentationType = "CSG"


def _storey_slab(
    ifc_file: ifcopenshell.file, storey: ifcopenshell.entity_instance
) -> ifcopenshell.entity_instance:
    for rel in storey.ContainsElements:
        for product in rel.RelatedElements:
            if product.is_a("IfcSlab") and product.Name != "Balkon":
                return product
    raise ValueError(f"no floor plate on storey {storey.Name!r}")


def generate_mep_riser(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Heating flow/return, supply duct and cable tray rising through the slabs."""
    params = dict(params or {})
    ifc_file, _primary = generate_spatial_structure(
        {
            "project_name": params.get("project_name") or "Steigzone",
            "highlight": "slab-floor",
            "plot_width": PLOT_WIDTH,
            "plot_depth": PLOT_DEPTH,
        }
    )
    storeys = sorted(
        ifc_file.by_type("IfcBuildingStorey"),
        key=lambda s: float(getattr(s, "Elevation", None) or 0.0),
    )
    scene = MepScene(ifc_file, get_body_context(ifc_file), storeys[0])
    f = ifc_file
    pipe_area = round(math.pi * PIPE_R**2, 4)

    # Faceted pipes get an edge per facet; thin edges keep the orange readable.
    run_z = ROOF - SOFFIT_GAP - PIPE_R
    scene.thin.append(
        scene.device(
            "mep-schematic-pipe",
            _pipe_run(f, PIPE_VL, run_z, PIPE_R),
            quantities={"Qto_PipeSegmentBaseQuantities": {"GrossCrossSectionArea": pipe_area}},
        )
    )
    scene.thin.append(
        scene.device(
            "mep-schematic-pipe",
            _pipe_run(f, PIPE_RL, run_z, PIPE_R),
            name="HZ-RL-01",
            property_overrides={"Reference": "RL-H"},
            quantities={"Qto_PipeSegmentBaseQuantities": {"GrossCrossSectionArea": pipe_area}},
        )
    )

    # L-bends below: each riser stops under its run and the run starts at the
    # riser's outer face, so the two solids touch without overlapping.
    dx, dy = DUCT_CENTER
    duct_z = ROOF - SOFFIT_GAP - DUCT_RUN[1] * 0.5
    duct_riser_top = duct_z - DUCT_RUN[1] * 0.5
    duct_run_start_x = dx + DUCT_RISER[0] * 0.5
    scene.device(
        "mep-schematic-duct",
        [
            duct_solid(f, (dx, dy, RISER_BOTTOM), (dx, dy, duct_riser_top), *DUCT_RISER),
            duct_solid(f, (duct_run_start_x, dy, duct_z), (RUN_END_X, dy, duct_z), *DUCT_RUN),
        ],
        quantities={
            "Qto_DuctSegmentBaseQuantities": {
                "GrossCrossSectionArea": round(DUCT_RISER[0] * DUCT_RISER[1], 4)
            }
        },
    )

    tx, ty = TRAY_CENTER
    tray_z = ROOF - SOFFIT_GAP - TRAY_RUN[1] * 0.5
    riser_top = tray_z - TRAY_RUN[1] * 0.5
    run_start_x = tx + TRAY_RISER[0] * 0.5
    scene.device(
        "mep-schematic-tray",
        [
            duct_solid(f, (tx, ty, RISER_BOTTOM), (tx, ty, riser_top), *TRAY_RISER),
            duct_solid(f, (run_start_x, ty, tray_z), (RUN_END_X, ty, tray_z), *TRAY_RUN),
        ],
    )

    # Roof drain at the front-left corner down to the base slab; balcony drain to the plot.
    downpipe_area = round(math.pi * DOWNPIPE_R**2, 4)
    rx, ry = DOWNPIPE_ROOF
    bx, by = DOWNPIPE_BALCONY
    for start, end in (
        ((rx, ry, RISER_BOTTOM), (rx, ry, ROOF + SLAB_T + 0.05)),
        ((bx, by, 0.0), (bx, by, FLOOR_01 + SLAB_T + 0.02)),
    ):
        scene.thin.append(
            scene.device(
                "mep-downpipe",
                [pipe_solid(f, start, end, DOWNPIPE_R)],
                quantities={
                    "Qto_PipeSegmentBaseQuantities": {"GrossCrossSectionArea": downpipe_area}
                },
            )
        )

    pad = 0.1
    downpipe_void = (rx - pad, ry - pad, rx + pad, ry + pad)
    for storey in storeys[1:]:
        _cut_slab_holes(f, _storey_slab(f, storey), [VOID_FOOTPRINT, downpipe_void])
    voids = (
        (VOID_FOOTPRINT, FLOOR_01),
        (VOID_FOOTPRINT, ROOF),
        (downpipe_void, FLOOR_01),
        (downpipe_void, ROOF),
    )
    void_card = params.get("highlight") == "mep-provision-for-void"
    for index, (footprint, slab_bottom) in enumerate(voids):
        void = scene.device(
            "mep-provision-for-void",
            [_void_box(f, footprint, slab_bottom)],
            property_overrides={"Reference": f"DB-{index + 1:02d}"},
        )
        if not void_card:
            scene.dotted.append(void)
    if params.get("highlight") in SEGMENT_SLUGS:
        scene.dotted.append(_storey_slab(f, storeys[-1]))
    return scene.finish(params)
