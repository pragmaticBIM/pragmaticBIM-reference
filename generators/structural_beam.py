"""IfcBeam Unterzug detailliert — one bearing wall with an elastomer pad."""

from __future__ import annotations

from typing import Any

import ifcopenshell

from generators.structural_core import (
    add_bearing_pad,
    add_solid_product,
    apply_attributes,
    box_solid,
    build_structural_core,
)

# Metres — detail cut through one bearing (the far support is not shown)
DEFAULT_SLAB_WIDTH = 4.0
DEFAULT_SLAB_DEPTH = 3.4
DEFAULT_WALL_SPAN = (0.5, 3.5)
DEFAULT_WALL_HEIGHT = 1.80
DEFAULT_BEAM_WIDTH = 0.30
DEFAULT_BEAM_DEPTH = 0.50
DEFAULT_BEAM_LENGTH = 2.60
DEFAULT_WALL_THICKNESS = 0.30
# Pad drawn thicker than reality and slightly wider than the beam so it
# reads at catalog scale; it stays inside the wall crown front and back.
PAD_INSET = 0.03
PAD_OVERHANG = 0.02
PAD_THICKNESS = 0.05


def generate_structural_beam(
    params: dict[str, Any],
) -> tuple[ifcopenshell.file, list[ifcopenshell.entity_instance]]:
    """Base slab + one bearing wall; orange beam on an elastomer pad.

    The beam sits on the wall crown and runs towards the camera, ending in a
    clean cut face. No floor slab, so the bearing reads from above.

    ``params`` keys:
    - ``attrs``: YAML-resolved attributes (structural-beam.yaml)
    - ``beam_width`` / ``beam_depth`` / ``beam_length`` / ``wall_height`` (m)

    Returns ``(ifc_file, [beam])``.
    """
    beam_w = float(params.get("beam_width", DEFAULT_BEAM_WIDTH))
    beam_d = float(params.get("beam_depth", DEFAULT_BEAM_DEPTH))
    beam_l = float(params.get("beam_length", DEFAULT_BEAM_LENGTH))
    if min(beam_w, beam_d, beam_l) <= 0:
        raise ValueError("beam dimensions must be positive")

    core = build_structural_core(
        {
            "project_name": params.get("project_name") or "Unterzug",
            "slab_width": float(params.get("slab_width", DEFAULT_SLAB_WIDTH)),
            "slab_depth": float(params.get("slab_depth", DEFAULT_SLAB_DEPTH)),
            "wall": "base",
            "wall_span": DEFAULT_WALL_SPAN,
            "wall_height": float(params.get("wall_height", DEFAULT_WALL_HEIGHT)),
            "wall_thickness": DEFAULT_WALL_THICKNESS,
            "include_column": False,
            "floor_slab": None,
        }
    )
    ifc_file = core.ifc_file
    cx = 0.5 * (core.wall_span[0] + core.wall_span[1])

    add_bearing_pad(
        core,
        name="EL-01",
        x0=cx - beam_w / 2 - PAD_OVERHANG,
        y0=PAD_INSET,
        x1=cx + beam_w / 2 + PAD_OVERHANG,
        y1=core.wall_thickness - PAD_INSET,
        z_bottom=core.wall_top,
        thickness=PAD_THICKNESS,
    )

    z_soffit = core.wall_top + PAD_THICKNESS
    beam = add_solid_product(
        core,
        ifc_class="IfcBeam",
        name="U-01",
        solids=box_solid(
            ifc_file, cx - beam_w / 2, 0.0, cx + beam_w / 2, beam_l, z_soffit, z_soffit + beam_d
        ),
        predefined_type="BEAM",
    )
    apply_attributes(
        ifc_file,
        beam,
        params.get("attrs"),
        quantities={"Qto_BeamBaseQuantities": {"GrossVolume": round(beam_w * beam_d * beam_l, 3)}},
    )
    return ifc_file, [beam]
