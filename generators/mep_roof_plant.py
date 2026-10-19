"""MEP roof plant (Dachzentrale) on the flat-roof / parapet vignette."""

from __future__ import annotations

from typing import Any

import ifcopenshell

from generators.base import get_body_context
from generators.mep_parts import MepScene, box_solid, duct_solid, vertical_cylinder_solid
from generators.roofing import DEFAULT_SLAB_THICKNESS, generate_roofing

# Metres — wider roof plate than the Gefälledämmung card; parapet on +Y.
ROOF_WIDTH = 7.0
ROOF_DEPTH = 5.0
# Plinths lift the plant above the tapered insulation (max 0.32 m).
_PLINTH_TOP = DEFAULT_SLAB_THICKNESS + 0.42

ROOF_PLANT_SLUGS = frozenset({"mep-cooling-tower", "mep-unitary-equipment", "mep-fan"})


def generate_mep_roof_plant(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Dry cooler, rooftop air handler and roof exhaust fan on plinths."""
    params = dict(params or {})
    ifc_file, _roofing = generate_roofing(
        {
            "project_name": params.get("project_name") or "Dachzentrale",
            "slab_width": ROOF_WIDTH,
            "slab_depth": ROOF_DEPTH,
        }
    )
    storey = ifc_file.by_type("IfcBuildingStorey")[0]
    scene = MepScene(ifc_file, get_body_context(ifc_file), storey)
    f = ifc_file
    z_roof = DEFAULT_SLAB_THICKNESS
    z0 = _PLINTH_TOP

    def plinth(name: str, x0: float, y0: float, x1: float, y1: float) -> None:
        scene.context(
            "IfcBuildingElementProxy",
            name,
            [box_solid(f, x0, y0, z_roof, x1, y1, z0)],
            predefined_type="USERDEFINED",
            object_type="Sockel",
        )

    # Dry cooler on two rails; two fan rings on top.
    plinth("Sockel-RK-1", 0.6, 0.7, 3.2, 0.9)
    plinth("Sockel-RK-2", 0.6, 1.5, 3.2, 1.7)
    scene.device(
        "mep-cooling-tower",
        [
            box_solid(f, 0.6, 0.6, z0, 3.2, 1.8, z0 + 1.1),
            vertical_cylinder_solid(f, 1.25, 1.2, z0 + 1.1, 0.45, 0.15, segments=16),
            vertical_cylinder_solid(f, 2.55, 1.2, z0 + 1.1, 0.45, 0.15, segments=16),
        ],
    )

    # Rooftop air handler; supply / extract ducts leave the end face and drop into the roof.
    plinth("Sockel-LA", 3.6, 0.5, 6.0, 1.7)
    scene.device("mep-unitary-equipment", [box_solid(f, 3.6, 0.5, z0, 6.0, 1.7, z0 + 1.4)])
    for name, y in (("Zuluft", 0.8), ("Abluft", 1.4)):
        scene.context(
            "IfcDuctSegment",
            f"{name}-horizontal",
            [duct_solid(f, (6.0, y, z0 + 0.9), (6.45, y, z0 + 0.9), 0.4, 0.4)],
        )
        scene.context(
            "IfcDuctSegment",
            f"{name}-vertikal",
            [duct_solid(f, (6.45, y, z0 + 1.1), (6.45, y, z_roof), 0.4, 0.4)],
        )

    # Roof exhaust fan on an upstand curb.
    scene.context(
        "IfcBuildingElementProxy",
        "Aufsatzkranz",
        [box_solid(f, 1.2, 2.8, z_roof, 1.9, 3.5, z0)],
        predefined_type="USERDEFINED",
        object_type="Sockel",
    )
    scene.device(
        "mep-fan",
        [
            box_solid(f, 1.2, 2.8, z0, 1.9, 3.5, z0 + 0.12),
            vertical_cylinder_solid(f, 1.55, 3.15, z0 + 0.12, 0.28, 0.40, segments=12),
            vertical_cylinder_solid(f, 1.55, 3.15, z0 + 0.52, 0.34, 0.06, segments=12),
        ],
    )
    return scene.finish(params)
