"""Render data-schema cards to catalog PNG + print TIFF."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from PIL import Image

from dataschema.scene import Scene, SceneResult
from render.engrave_specs import EngraveSpec
from render.isometric import (
    DEFAULT_RESOLUTION,
    PRINT_DPI,
    PRINT_RESOLUTION,
    _framing_bounds,
    _product_meshes,
    render_isometric,
)
from render.print_raster import PRINT_BG_RGB, save_print_tiff


@dataclass(frozen=True)
class Card:
    """One data-schema element picture: scene builder + accented keys + framing."""

    build: Callable[..., Scene]
    highlight: str | tuple[str, ...]
    kwargs: dict[str, Any] = field(default_factory=dict)
    camera_padding: float = 1.6
    camera_direction: Sequence[float] | None = None
    # Scene keys the camera frames; empty frames the whole scene.
    camera_focus: tuple[str, ...] = ()
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


def _focus_guids(card: Card, scene: Scene) -> set[str] | None:
    return {p.GlobalId for key in card.camera_focus for p in scene.groups.get(key, ())} or None


def _common(card: Card, scene: Scene, result: SceneResult, accent: Sequence[float] | None) -> dict[str, Any]:
    return dict(
        primary_guids={p.GlobalId for p in result.primary},
        primary_colors=result.colors or None,
        dotted_guids={p.GlobalId for p in result.dotted} or None,
        thin_edge_guids={p.GlobalId for p in result.thin} or None,
        camera_padding=card.camera_padding,
        camera_direction=card.camera_direction,
        camera_focus_guids=_focus_guids(card, scene),
        color_flooring=False,
        accent=accent,
    )


def render_card(
    card_id: str,
    card: Card,
    image_dir: Path,
    ifc_dir: Path | None = None,
    *,
    accent: Sequence[float] | None = None,
    brand: bool = True,
    watermark: bool | None = None,
    system: bool = False,
) -> tuple[Path, Path]:
    """``system`` renders the picture of a system: pipes, cables and trays serving the accent are accented too.

    ``watermark`` defaults to ``brand``; turn it off to add the corner label after overlays.
    """
    scene = card.build(**card.kwargs)
    result = scene.result(card.highlight, system=system)
    if ifc_dir is not None:
        ifc_dir.mkdir(parents=True, exist_ok=True)
        result.ifc_file.write(str(ifc_dir / f"{card_id}.ifc"))
    image_dir.mkdir(parents=True, exist_ok=True)
    png = image_dir / f"{card_id}.png"
    tif = image_dir / f"{card_id}-print.tif"
    common = _common(card, scene, result, accent)
    render_isometric(
        result.ifc_file,
        png,
        engrave=brand,
        watermark=brand if watermark is None else watermark,
        **common,
        **_engrave_kwargs(card.engrave),
    )
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


_FIT_MARGIN = 0.06
_BG_TOL = 6


def _content_mask(image: Image.Image) -> np.ndarray:
    arr = np.asarray(image.convert("RGB"), dtype=np.int16)
    return np.abs(arr - np.asarray(PRINT_BG_RGB, dtype=np.int16)).max(axis=2) > _BG_TOL


def _fit_square(images: Sequence[Image.Image], size: Sequence[int]) -> list[Image.Image]:
    """Crop every image to the set's common content box, pad it square and scale it to ``size``."""
    mask = np.logical_or.reduce([_content_mask(image) for image in images])
    ys, xs = np.where(mask)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    w, h = box[2] - box[0], box[3] - box[1]
    pad = max(1, round(max(w, h) * _FIT_MARGIN))
    side = max(w, h) + 2 * pad
    out = []
    for image in images:
        canvas = Image.new("RGB", (side, side), PRINT_BG_RGB)
        canvas.paste(image.convert("RGB").crop(box), ((side - w) // 2, (side - h) // 2))
        out.append(canvas.resize(tuple(size), Image.Resampling.LANCZOS))
    return out


def render_card_set(
    set_id: str,
    cards: Sequence[tuple[str, Card]],
    image_dir: Path,
    ifc_dir: Path | None = None,
    *,
    accent: Sequence[float] | None = None,
    decorate: Callable[[Image.Image, np.ndarray], Image.Image] | None = None,
) -> dict[str, tuple[Path, Path]]:
    """One orthographic picture per card with a shared camera, scale and framing, so the set compares 1:1.

    ``decorate(image, mask)`` draws overlays such as the hierarchy tree; ``mask`` is the content of the
    whole set at that resolution, so every picture makes room the same way.
    Returns card name → (PNG, print TIF) named ``{set_id}-{name}``.
    """
    built = []
    for name, card in cards:
        scene = card.build(**card.kwargs)
        result = scene.result(card.highlight)
        if ifc_dir is not None:
            ifc_dir.mkdir(parents=True, exist_ok=True)
            result.ifc_file.write(str(ifc_dir / f"{set_id}-{name}.ifc"))
        common = _common(card, scene, result, accent)
        meshes = _product_meshes(result.ifc_file, primary_guids=common["primary_guids"])
        built.append((name, result, common, _framing_bounds(meshes, camera_focus_guids=common["camera_focus_guids"])))
    bounds = np.array([np.min([b[0] for *_, b in built], axis=0), np.max([b[1] for *_, b in built], axis=0)])

    image_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, list[Path]] = {name: [] for name, *_ in built}
    for resolution, suffix in ((DEFAULT_RESOLUTION, ".png"), (PRINT_RESOLUTION, "-print.tif")):
        raw = []
        for name, result, common, _ in built:
            path = image_dir / f"{set_id}-{name}-raw.png"
            render_isometric(
                result.ifc_file,
                path,
                resolution=resolution,
                orthographic=True,
                camera_bounds=bounds,
                fit_content=False,
                engrave=False,
                watermark=False,
                **common,
            )
            with Image.open(path) as im:
                raw.append(im.convert("RGB"))
            path.unlink()
        images = _fit_square(raw, resolution)
        mask = np.logical_or.reduce([_content_mask(image) for image in images])
        for (name, *_), image in zip(built, images):
            if decorate is not None:
                image = decorate(image, mask)
            path = image_dir / f"{set_id}-{name}{suffix}"
            if suffix.endswith(".tif"):
                save_print_tiff(image, path)
            else:
                image.save(path)
            paths[name].append(path)
    return {name: (png, tif) for name, (png, tif) in paths.items()}
