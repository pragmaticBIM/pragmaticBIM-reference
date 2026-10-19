"""Render data-schema cards to catalog PNG + print TIFF."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from dataschema.scene import Scene
from render.engrave_specs import EngraveSpec
from render.isometric import PRINT_DPI, PRINT_RESOLUTION, render_isometric


@dataclass(frozen=True)
class Card:
    """One data-schema element picture: scene builder + accented keys + framing."""

    build: Callable[..., Scene]
    highlight: str | tuple[str, ...]
    kwargs: dict[str, Any] = field(default_factory=dict)
    camera_padding: float = 1.6
    camera_direction: Sequence[float] | None = None
    engrave: EngraveSpec = EngraveSpec()


def _engrave_kwargs(spec: EngraveSpec) -> dict[str, Any]:
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


def render_card(card_id: str, card: Card, image_dir: Path, ifc_dir: Path | None = None) -> tuple[Path, Path]:
    scene = card.build(**card.kwargs)
    result = scene.result(card.highlight)
    if ifc_dir is not None:
        ifc_dir.mkdir(parents=True, exist_ok=True)
        result.ifc_file.write(str(ifc_dir / f"{card_id}.ifc"))
    image_dir.mkdir(parents=True, exist_ok=True)
    png = image_dir / f"{card_id}.png"
    tif = image_dir / f"{card_id}-print.tif"
    common = dict(
        primary_guids={p.GlobalId for p in result.primary},
        primary_colors=result.colors or None,
        dotted_guids={p.GlobalId for p in result.dotted} or None,
        thin_edge_guids={p.GlobalId for p in result.thin} or None,
        camera_padding=card.camera_padding,
        camera_direction=card.camera_direction,
        color_flooring=False,
    )
    render_isometric(result.ifc_file, png, **common, **_engrave_kwargs(card.engrave))
    render_isometric(
        result.ifc_file,
        tif,
        resolution=PRINT_RESOLUTION,
        engrave=False,
        watermark=False,
        dpi=PRINT_DPI,
        **common,
    )
    return png, tif
