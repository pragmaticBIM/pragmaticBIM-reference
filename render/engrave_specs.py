"""Explicit per-picture brand-engraving placement for catalog PNGs.

Placement is keyed by catalog entry ``id`` so tuning one card does not
change another. Host selection remains geometric. Letter size is shared:
the renderer sizes the wordmark from the camera frame.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EngraveSpec:
    """Render-only brand carve options for one catalog picture."""

    prefer_lowest: bool = False
    far_corner: bool = False
    side_corner: bool = False
    prefer_wall: bool = False
    longest_wall: bool = False
    wall_top: bool = False
    rotate_90: bool = False
    # Place mid-face along the wall length (not at the tip corner).
    center_along_wall: bool = False
    # Optional exact IfcWall.Name host for this picture.
    wall_name: str | None = None


# Defaults: highest horizontal plate.
_DEFAULT = EngraveSpec()

# MEP vignettes share one placement per scene (see catalog/sample_data_mep.py).
_MEP_ENGRAVE_BY_SCENE: tuple[tuple[tuple[str, ...], EngraveSpec], ...] = (
    (
        (
            "mep-boiler",
            "mep-heat-exchanger",
            "mep-chiller",
            "mep-pump",
            "mep-compressor",
            "mep-gas-regulator",
            "mep-tank",
            "mep-schematic-equipment-space",
            "mep-transformer",
            "mep-ups",
            "mep-electric-distribution-board",
            "mep-electric-generator",
        ),
        EngraveSpec(prefer_wall=True, wall_name="Rueckwand", wall_top=True),
    ),
    (
        ("mep-cooling-tower", "mep-unitary-equipment", "mep-fan"),
        EngraveSpec(prefer_wall=True, wall_top=True),
    ),
    (
        (
            "mep-air-terminal",
            "mep-light-fixture",
            "mep-alarm",
            "mep-fire-suppression-terminal",
            "mep-cooled-beam",
            "mep-air-terminal-box",
            "mep-damper",
            "mep-actuator",
        ),
        EngraveSpec(prefer_lowest=True),
    ),
    (
        (
            "mep-switching-device",
            "mep-outlet",
            "mep-sensor",
            "mep-communications-appliance",
        ),
        EngraveSpec(prefer_wall=True, wall_name="Trennwand", wall_top=True),
    ),
    (
        ("mep-space-heater", "mep-valve", "mep-gas-terminal"),
        EngraveSpec(prefer_wall=True, wall_name="Aussenwand", wall_top=True),
    ),
    (
        ("mep-sanitary-terminal", "mep-waste-terminal"),
        EngraveSpec(prefer_wall=True, wall_name="Rueckwand", wall_top=True),
    ),
    # Riser pokes through the roof plate; brand goes on the plot in front.
    (
        (
            "mep-schematic-pipe",
            "mep-schematic-duct",
            "mep-schematic-tray",
            "mep-downpipe",
            "mep-provision-for-void",
        ),
        EngraveSpec(prefer_lowest=True),
    ),
)

# Fixed per catalog picture id (see catalog/sample_data.py).
ENGRAVE_BY_ID: dict[str, EngraveSpec] = {
    **{
        f"{slug}-01": spec
        for slugs, spec in _MEP_ENGRAVE_BY_SCENE
        for slug in slugs
    },
    # Horizontal plates -------------------------------------------------
    "coordination-zone-01": EngraveSpec(prefer_lowest=True),
    "stair-01": EngraveSpec(prefer_lowest=True),
    "railing-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "installation-path-01": EngraveSpec(
        prefer_wall=True,
        wall_name="Flur-Wand-Unten",
        wall_top=True,
        rotate_90=True,
        center_along_wall=True,
    ),
    "turning-radius-01": EngraveSpec(prefer_lowest=True),
    "decision-volume-01": EngraveSpec(prefer_lowest=True),
    "movement-clearance-01": EngraveSpec(
        prefer_wall=True,
        wall_name="Rueckwand",
        wall_top=True,
    ),
    "building-law-parcel-01": EngraveSpec(prefer_lowest=True),
    "surrounding-building-01": EngraveSpec(prefer_lowest=True),
    "construction-logistics-01": EngraveSpec(prefer_lowest=True),
    "planning-constraint-01": EngraveSpec(prefer_lowest=True),
    "umbau-perimeter-01": EngraveSpec(prefer_lowest=True),
    "cladding-exterior-01": EngraveSpec(prefer_lowest=True),
    "footing-pad-01": EngraveSpec(far_corner=True),
    # Structural cards: base slab in front of the subject.
    "structural-exclusion-zone-01": EngraveSpec(prefer_lowest=True),
    "structural-beam-01": EngraveSpec(prefer_lowest=True),
    "structural-slab-roof-01": EngraveSpec(prefer_lowest=True),
    "structural-stair-01": EngraveSpec(prefer_lowest=True),
    "structural-ramp-01": EngraveSpec(prefer_lowest=True),
    "structural-wall-01": EngraveSpec(prefer_lowest=True),
    "structural-column-01": EngraveSpec(prefer_lowest=True),
    "structural-slab-floor-01": EngraveSpec(prefer_lowest=True),
    "structural-slab-base-01": EngraveSpec(prefer_lowest=True),
    "structural-rebar-01": EngraveSpec(prefer_lowest=True),
    # Column: near-corner brand so text sits in front of the centred column.
    "column-01": EngraveSpec(),
    # Tree: lateral terrain tip so the crown does not hide the brand.
    "tree-01": EngraveSpec(side_corner=True),
    "retention-01": EngraveSpec(side_corner=True),
    # Furniture: brand on the back wall (same as other interior wall cards).
    "furniture-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "built-in-furniture-kitchen-01": EngraveSpec(prefer_wall=True, wall_top=True),
    # Vertical facades --------------------------------------------------
    "space-parking-01": EngraveSpec(prefer_wall=True),
    "space-elevator-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "space-vorsatzschale-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "detail-reference-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "wall-exterior-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "wall-interior-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "wall-interior-lb-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "drywall-reinforcement-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "wall-cladding-interior-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "door-exterior-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "window-exterior-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "shading-device-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "door-interior-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "window-interior-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "roofing-insulation-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "roof-overflow-01": EngraveSpec(prefer_wall=True, wall_top=True),
    "structural-footing-01": EngraveSpec(prefer_wall=True, wall_top=True),
}


def engrave_spec_for(entry_id: str) -> EngraveSpec:
    """Return the fixed engraving spec for a catalog entry id."""
    return ENGRAVE_BY_ID.get(str(entry_id), _DEFAULT)


def engrave_kwargs_for(entry_id: str) -> dict[str, Any]:
    """Keyword args for ``render_isometric`` (``engrave_*`` parameters)."""
    spec = engrave_spec_for(entry_id)
    return {
        "engrave_prefer_lowest": spec.prefer_lowest,
        "engrave_far_corner": spec.far_corner,
        "engrave_side_corner": spec.side_corner,
        "engrave_prefer_wall": spec.prefer_wall,
        "engrave_longest_wall": spec.longest_wall,
        "engrave_wall_top": spec.wall_top,
        "engrave_rotate_90": spec.rotate_90,
        "engrave_center_along_wall": spec.center_along_wall,
        "engrave_wall_name": spec.wall_name,
    }


def engrave_spec_as_dict(entry_id: str) -> dict[str, Any]:
    """Plain dict of the EngraveSpec fields (debug / logging)."""
    return asdict(engrave_spec_for(entry_id))
