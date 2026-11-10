"""MEP bathroom (Bad) — reuses the accessible wet-room vignette without clearances."""

from __future__ import annotations

from typing import Any

import ifcopenshell
from ifcopenshell.api.root import reassign_class, remove_product

from generators.base import get_body_context
from generators.mep_parts import MepScene, box_solid
from generators.movement_clearance import (
    DEFAULT_BASIN_DEPTH,
    DEFAULT_BASIN_HEIGHT,
    DEFAULT_BASIN_OFFSET_X,
    DEFAULT_BASIN_RIM,
    DEFAULT_BASIN_WIDTH,
    DEFAULT_SHOWER_RECESS,
    DEFAULT_WALL_LEFT,
    DEFAULT_WALL_OTHER,
    DEFAULT_INTERIOR_DEPTH,
    generate_movement_clearance,
)

BATHROOM_SLUGS = frozenset({"mep-sanitary-terminal", "mep-waste-terminal"})

# Shower recess footprint as built by generate_movement_clearance; the drain sits
# toward the left wall so the WC does not hide it from the camera.
_SHOWER_SIZE = 1.15
_DRAIN_SIZE = 0.20
_DRAIN_OFFSET_X = 0.40

# Basin bowl: rim widths (sides / front, back) and depth below the rim.
_BOWL_RIM_SIDE = 0.05
_BOWL_RIM_BACK = 0.09
_BOWL_DEPTH = 0.10
# Trap below the basin: vertical drop, then a horizontal run into the back wall.
_TRAP_SIZE = 0.07
_TRAP_DROP = 0.36
_TRAP_WALL_DEPTH = 0.03

# (vignette Name, IFC4 PredefinedType, Name on the sanitary card)
_SANITARY_PARTS = (
    ("WC", "TOILETPAN", "WC-01"),
    ("WC-Spuelkasten", "CISTERN", "SK-01"),
    ("Waschbecken", "WASHHANDBASIN", "WT-01"),
    ("Dusche", "SHOWER", "DU-01"),
)


def _shape_basin(ifc_file: ifcopenshell.file, basin: ifcopenshell.entity_instance) -> None:
    """Open the basin top with a bowl and add the box trap below it.

    The back rim stays wider for the tap; the trap drops from the basin and
    runs back into the wall. Coordinates are in the basin frame (z = 0 at its
    underside).
    """
    x0 = DEFAULT_WALL_LEFT + DEFAULT_BASIN_OFFSET_X
    y0 = DEFAULT_WALL_OTHER
    representation = basin.Representation.Representations[0]
    cutter = box_solid(
        ifc_file,
        x0 + _BOWL_RIM_SIDE,
        y0 + _BOWL_RIM_BACK,
        DEFAULT_BASIN_HEIGHT - _BOWL_DEPTH,
        x0 + DEFAULT_BASIN_WIDTH - _BOWL_RIM_SIDE,
        y0 + DEFAULT_BASIN_DEPTH - _BOWL_RIM_SIDE,
        DEFAULT_BASIN_HEIGHT + 0.01,
    )
    body = ifc_file.create_entity(
        "IfcBooleanResult",
        Operator="DIFFERENCE",
        FirstOperand=representation.Items[0],
        SecondOperand=cutter,
    )

    cx = x0 + DEFAULT_BASIN_WIDTH * 0.5
    cy = y0 + (_BOWL_RIM_BACK + DEFAULT_BASIN_DEPTH - _BOWL_RIM_SIDE) * 0.5
    half = _TRAP_SIZE * 0.5
    drop = box_solid(ifc_file, cx - half, cy - half, -_TRAP_DROP, cx + half, cy + half, 0.0)
    run = box_solid(
        ifc_file,
        cx - half,
        y0 - _TRAP_WALL_DEPTH,
        -_TRAP_DROP,
        cx + half,
        cy - half,
        -_TRAP_DROP + _TRAP_SIZE,
    )
    for trap in (drop, run):
        body = ifc_file.create_entity(
            "IfcBooleanResult", Operator="UNION", FirstOperand=body, SecondOperand=trap
        )
    representation.Items = [body]
    representation.RepresentationType = "CSG"


def generate_mep_bathroom(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """WC, cistern, washbasin and shower as IfcSanitaryTerminal; floor drain in the shower recess."""
    params = dict(params or {})
    ifc_file, clearances = generate_movement_clearance(
        {"project_name": params.get("project_name") or "Bad"}
    )
    for proxy in clearances:
        remove_product(ifc_file, product=proxy)

    storey = ifc_file.by_type("IfcBuildingStorey")[0]
    scene = MepScene(ifc_file, get_body_context(ifc_file), storey)

    by_name = {p.Name: p for p in ifc_file.by_type("IfcBuildingElementProxy")}
    for vignette_name, predefined, card_name in _SANITARY_PARTS:
        terminal = reassign_class(
            ifc_file,
            product=by_name[vignette_name],
            ifc_class="IfcSanitaryTerminal",
            predefined_type=predefined,
        )
        terminal.Name = card_name
        scene.register(
            "mep-sanitary-terminal",
            terminal,
            name=card_name,
            predefined_type=predefined,
        )
        if predefined == "WASHHANDBASIN":
            _shape_basin(ifc_file, terminal)

    x0 = DEFAULT_WALL_LEFT
    y1 = DEFAULT_WALL_OTHER + DEFAULT_INTERIOR_DEPTH
    cx = x0 + _DRAIN_OFFSET_X
    cy = y1 - _SHOWER_SIZE * 0.5
    half = _DRAIN_SIZE * 0.5
    scene.device(
        "mep-waste-terminal",
        [box_solid(ifc_file, cx - half, cy - half, -DEFAULT_SHOWER_RECESS, cx + half, cy + half, 0.012)],
    )
    return scene.finish(params)
