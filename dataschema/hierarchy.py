"""IFC hierarchy tree drawn in the top-left corner of element pictures.

Virtual elements highlight their own node; every other element adds a row
with its IFC class below the storey.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from render.isometric import _apply_corner_watermark, _load_font
from render.print_raster import PRINT_BG_RGB, save_print_tiff

NODE_BY_ENTITY: dict[str, str] = {
    "IfcProject": "project",
    "IfcSite": "site",
    "IfcBuilding": "building",
    "IfcBuildingStorey": "storey",
    "IfcDistributionSystem": "system",
    "IfcBuildingSystem": "system",
    "IfcZone": "zone",
}

# (key, label, depth, parent, dashed): dashed connectors are groupings, not aggregation.
_ROWS: tuple[tuple[str, str, int, str | None, bool], ...] = (
    ("project", "IfcProject", 0, None, False),
    ("site", "IfcSite", 1, "project", False),
    ("building", "IfcBuilding", 2, "site", False),
    ("storey", "IfcBuildingStorey", 3, "building", False),
    ("system", "IfcSystem", 1, "project", True),
    ("zone", "IfcZone", 1, "project", True),
)
ELEMENT = "element"

_INK = (30, 30, 30)
_WHITE = (255, 255, 255)
_ACCENT = (212, 49, 49)
# Layout in pixels of a 1024 px picture; scaled to the image width.
_FONT = 19
_BOX_H = 30
_PITCH = 40
_INDENT = 26
_PAD_X = 9
_LINE = 2
_MARGIN = 26
_PANEL_PAD = 8
_DASH = 5
# Clear space between the tree and the picture content.
_GAP = 14
_BG_TOL = 6
# Content moved out of the tree's corner keeps this fraction of the width to the bottom-right edges.
_EDGE_MARGIN = 0.05
# Filled fraction of the content's top row or left column above which the picture counts as cropped.
_CROP_EDGE = 0.4
# Rows / columns searched for that edge; the crop border is antialiased.
_CROP_DEPTH = 8
# Drawn oversampled and scaled down for smooth edges and text.
_SUPERSAMPLE = 3


def _dashed(draw: ImageDraw.ImageDraw, a: tuple[float, float], b: tuple[float, float], dash: float, width: int) -> None:
    (x0, y0), (x1, y1) = a, b
    length = max(abs(x1 - x0), abs(y1 - y0))
    steps = max(1, int(length // dash))
    for i in range(0, steps, 2):
        t0, t1 = i / steps, min(i + 1, steps) / steps
        draw.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0), (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)], fill=_INK, width=width)


def _rows(element: str | None) -> tuple[tuple[str, str, int, str | None, bool], ...]:
    if element is None:
        return _ROWS
    at = next(i for i, row in enumerate(_ROWS) if row[0] == "storey") + 1
    return (*_ROWS[:at], (ELEMENT, element, 4, "storey", False), *_ROWS[at:])


def _panel(active: str, scale: float, accent: tuple[int, int, int], element: str | None = None) -> Image.Image:
    rows = _rows(element)
    font = _load_font(max(8, round(_FONT * scale)))
    box_h, pitch, indent = _BOX_H * scale, _PITCH * scale, _INDENT * scale
    pad_x, pad = _PAD_X * scale, _PANEL_PAD * scale
    line = max(1, round(_LINE * scale))

    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    boxes: dict[str, tuple[float, float, float, float]] = {}
    for row, (key, label, depth, _parent, _dashed_link) in enumerate(rows):
        x0 = pad + depth * indent
        y0 = pad + row * pitch
        bbox = probe.textbbox((0, 0), label, font=font)
        boxes[key] = (x0, y0, x0 + (bbox[2] - bbox[0]) + 2 * pad_x, y0 + box_h)
    width = max(b[2] for b in boxes.values()) + pad
    height = max(b[3] for b in boxes.values()) + pad

    panel = Image.new("RGBA", (round(width), round(height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    for key, _label, _depth, parent, dashed in rows:
        if parent is None:
            continue
        px0, _py0, _px1, py1 = boxes[parent]
        cx0, cy0, _cx1, cy1 = boxes[key]
        stem = px0 + indent * 0.5
        mid = (cy0 + cy1) * 0.5
        if dashed:
            _dashed(draw, (stem, py1), (stem, mid), _DASH * scale, line)
            _dashed(draw, (stem, mid), (cx0, mid), _DASH * scale, line)
        else:
            draw.line([(stem, py1), (stem, mid), (cx0, mid)], fill=_INK, width=line, joint="curve")
    # Light accents (Reference orange) need dark text on the active node.
    active_text = _INK if 0.299 * accent[0] + 0.587 * accent[1] + 0.114 * accent[2] > 160 else _WHITE
    for key, label, _depth, _parent, _dashed_link in rows:
        x0, y0, x1, y1 = boxes[key]
        on = key == active
        draw.rounded_rectangle((x0, y0, x1, y1), radius=4 * scale, fill=accent if on else _WHITE, outline=_INK, width=line)
        draw.text((x0 + pad_x, (y0 + y1) * 0.5), label, font=font, fill=active_text if on else _INK, anchor="lm")
    return panel


def _make_room(image: Image.Image, keep_out: tuple[int, int, int, int], mask: np.ndarray | None = None) -> Image.Image:
    """Move the content into the bottom-right margin corner, shrinking it until none lies in ``keep_out``.

    ``mask`` replaces the image's own content mask so pictures of one set move identically.
    """
    shared = mask is not None
    if mask is None:
        arr = np.asarray(image)
        mask = np.abs(arr.astype(np.int16) - np.asarray(PRINT_BG_RGB, dtype=np.int16)).max(axis=2) > _BG_TOL
    if not mask.any():
        return image
    ys, xs = np.where(mask)
    cx0, cy0, cx1, cy1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    # Cropped close-ups (straight top or left content edge) would show a hard frame when moved; the panel covers them instead.
    edge = mask[cy0:cy1, cx0:cx1]
    if not shared and max(edge[:_CROP_DEPTH].mean(axis=1).max(), edge[:, :_CROP_DEPTH].mean(axis=0).max()) > _CROP_EDGE:
        return image
    kx0, ky0, kx1, ky1 = keep_out

    def clear(s: float, ax: float, ay: float) -> bool:
        # keep_out mapped back into the source picture; content corner (cx1, cy1) lands on (ax, ay).
        x0, x1 = max(0, int(cx1 - (ax - kx0) / s)), int(np.ceil(cx1 - (ax - kx1) / s))
        y0, y1 = max(0, int(cy1 - (ay - ky0) / s)), int(np.ceil(cy1 - (ay - ky1) / s))
        return x1 <= x0 or y1 <= y0 or not mask[y0:y1, x0:x1].any()

    if clear(1.0, cx1, cy1):
        return image
    margin = round(_EDGE_MARGIN * image.width)
    ax, ay = max(cx1, image.width - margin), max(cy1, image.height - margin)
    s = 1.0
    while s > 0.5 and not clear(s, ax, ay):
        s -= 0.01
    content = image.crop((cx0, cy0, cx1, cy1))
    w, h = max(1, round((cx1 - cx0) * s)), max(1, round((cy1 - cy0) * s))
    out = Image.new("RGB", image.size, PRINT_BG_RGB)
    out.paste(content.resize((w, h), Image.Resampling.LANCZOS), (ax - w, ay - h))
    return out


def node_for(entity: str) -> tuple[str, str | None]:
    """``(active node, element label)`` for an IFC class: virtual nodes, otherwise an element below the storey."""
    if entity in NODE_BY_ENTITY:
        return NODE_BY_ENTITY[entity], None
    return ELEMENT, entity


def draw_hierarchy(
    image: Image.Image,
    active: str,
    accent: tuple[int, int, int] = _ACCENT,
    element: str | None = None,
    mask: np.ndarray | None = None,
) -> Image.Image:
    """Paste the tree with ``active`` highlighted into the top-left corner of ``image``.

    ``element`` adds a row with that label below the storey (active node ``"element"``).
    Content reaching into the corner is scaled down towards the bottom right first;
    ``mask`` (content of a whole picture set) makes every picture of the set move the same way.
    """
    if active not in {row[0] for row in _rows(element)}:
        raise ValueError(f"unknown hierarchy node {active!r}")
    out = image.convert("RGB")
    scale = out.width / 1024
    big = _panel(active, scale * _SUPERSAMPLE, accent, element)
    # Premultiplied alpha keeps the transparent surround from bleeding dark fringes into the edges.
    size = (round(big.width / _SUPERSAMPLE), round(big.height / _SUPERSAMPLE))
    panel = big.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    margin = round((_MARGIN - _PANEL_PAD) * scale)
    gap = round(_GAP * scale)
    out = _make_room(out, (0, 0, margin + panel.width + gap, margin + panel.height + gap), mask)
    out.paste(panel, (margin, margin), panel)
    return out


def apply_hierarchy(
    png: Path,
    tif: Path | None,
    active: str,
    accent: tuple[int, int, int] = _ACCENT,
    watermark: bool = False,
    element: str | None = None,
) -> None:
    """Draw the tree onto a placed catalog PNG and its CMYK print TIF in place.

    ``watermark`` adds the corner label to the PNG after the content has been moved.
    """
    with Image.open(png) as im:
        dpi = im.info.get("dpi")
        drawn = draw_hierarchy(im, active, accent, element)
    if watermark:
        drawn = _apply_corner_watermark(drawn)
    drawn.save(png, **({"dpi": dpi} if dpi else {}))
    if tif is None:
        return
    with Image.open(tif) as im:
        drawn = draw_hierarchy(im.convert("RGB"), active, accent, element)
    save_print_tiff(drawn, tif)
