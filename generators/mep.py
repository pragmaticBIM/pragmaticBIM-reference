"""MEP catalog pictures — dispatches each highlighted element to its vignette."""

from __future__ import annotations

from typing import Any, Callable

import ifcopenshell

from generators.mep_bathroom import BATHROOM_SLUGS, generate_mep_bathroom
from generators.mep_office_ceiling import OFFICE_CEILING_SLUGS, generate_mep_office_ceiling
from generators.mep_plant_room import (
    ELECTRICAL_ROOM_SLUGS,
    EQUIPMENT_SPACE_SLUG,
    PLANT_ROOM_SLUGS,
    generate_mep_electrical_room,
    generate_mep_plant_room,
)
from generators.mep_riser import RISER_SLUGS, generate_mep_riser
from generators.mep_roof_plant import ROOF_PLANT_SLUGS, generate_mep_roof_plant
from generators.mep_wall_devices import (
    WALL_ELECTRO_SLUGS,
    WALL_HEATING_SLUGS,
    generate_mep_wall_electro,
    generate_mep_wall_heating,
)

# Rendered as translucent volumes rather than solid devices.
MEP_VOLUME_SLUGS = frozenset({EQUIPMENT_SPACE_SLUG, "mep-provision-for-void"})

_SCENES: tuple[tuple[frozenset[str], Callable[..., Any]], ...] = (
    (PLANT_ROOM_SLUGS, generate_mep_plant_room),
    (ELECTRICAL_ROOM_SLUGS, generate_mep_electrical_room),
    (ROOF_PLANT_SLUGS, generate_mep_roof_plant),
    (OFFICE_CEILING_SLUGS, generate_mep_office_ceiling),
    (WALL_ELECTRO_SLUGS, generate_mep_wall_electro),
    (WALL_HEATING_SLUGS, generate_mep_wall_heating),
    (BATHROOM_SLUGS, generate_mep_bathroom),
    (RISER_SLUGS, generate_mep_riser),
)


def generate_mep(
    params: dict[str, Any] | None = None,
) -> tuple[ifcopenshell.file, list, list, list]:
    """Build the vignette that contains ``params["highlight"]`` and accent that element."""
    params = dict(params or {})
    highlight = str(params.get("highlight") or "")
    for slugs, generator in _SCENES:
        if highlight in slugs:
            return generator(params)
    raise ValueError(f"no MEP vignette for highlight {highlight!r}")
