"""SVG helpers for plan symbols (local metres → SVG document)."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from generators.component_geometry.types import SvgPath
from generators import room_rules as rr


def rect(x: float, y: float, w: float, h: float, **style) -> SvgPath:
    return SvgPath(
        d="",
        kind="rect",
        attrs={"x": x, "y": y, "width": w, "height": h},
        **{k: v for k, v in style.items() if k in ("fill", "stroke", "stroke_width", "stroke_dasharray")},
    )


def circle(cx: float, cy: float, r: float, **style) -> SvgPath:
    return SvgPath(
        d="",
        kind="circle",
        attrs={"cx": cx, "cy": cy, "r": r},
        **{k: v for k, v in style.items() if k in ("fill", "stroke", "stroke_width", "stroke_dasharray")},
    )


def ellipse(cx: float, cy: float, rx: float, ry: float, **style) -> SvgPath:
    return SvgPath(
        d="",
        kind="ellipse",
        attrs={"cx": cx, "cy": cy, "rx": rx, "ry": ry},
        **{k: v for k, v in style.items() if k in ("fill", "stroke", "stroke_width", "stroke_dasharray")},
    )


def line(x1: float, y1: float, x2: float, y2: float, **style) -> SvgPath:
    return SvgPath(
        d="",
        kind="line",
        attrs={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        **{k: v for k, v in style.items() if k in ("fill", "stroke", "stroke_width", "stroke_dasharray")},
    )


def path(d: str, **style) -> SvgPath:
    return SvgPath(
        d=d,
        kind="path",
        **{k: v for k, v in style.items() if k in ("fill", "stroke", "stroke_width", "stroke_dasharray")},
    )


def footprint_rect(width: float, depth: float, *, fill: str = "#f5f5f5") -> SvgPath:
    return rect(0.0, 0.0, width, depth, fill=fill, stroke="#1a1a1a", stroke_width=0.015)


def door_swing_arc(
    width: float,
    *,
    hinge_at_start: bool = True,
    sweep_into_room: bool = True,
) -> SvgPath:
    """Quarter-circle leaf swing in plan (local axes: X along opening, Y into room)."""
    r = width
    if hinge_at_start:
        # hinge at (0,0), latch at (width,0); swing to (0, width) or outside
        end_y = r if sweep_into_room else -r
        # SVG arc: from latch toward front
        large = 0
        sweep = 1 if sweep_into_room else 0
        d = f"M {width:.4f} 0 L 0 0 A {r:.4f} {r:.4f} 0 {large} {sweep} 0 {end_y:.4f}"
    else:
        end_y = r if sweep_into_room else -r
        sweep = 0 if sweep_into_room else 1
        d = f"M 0 0 L {width:.4f} 0 A {r:.4f} {r:.4f} 0 0 {sweep} {width:.4f} {end_y:.4f}"
    return path(d, fill="none", stroke="#1a1a1a", stroke_width=0.015)


def transform_local_to_room(paths: Sequence[SvgPath], frame: rr.Frame) -> list[SvgPath]:
    """Map local (u,v) paths into room XY. Circles/ellipses become paths when rotated."""
    ox, oy = frame.origin
    xx, xy = frame.x_axis
    yx, yy = frame.y_axis

    def map_pt(u: float, v: float) -> tuple[float, float]:
        return (ox + u * xx + v * yx, oy + u * xy + v * yy)

    out: list[SvgPath] = []
    for p in paths:
        if p.kind == "rect":
            x = float(p.attrs["x"])
            y = float(p.attrs["y"])
            w = float(p.attrs["width"])
            h = float(p.attrs["height"])
            pts = [map_pt(x, y), map_pt(x + w, y), map_pt(x + w, y + h), map_pt(x, y + h)]
            d = "M " + " L ".join(f"{a:.4f} {b:.4f}" for a, b in pts) + " Z"
            out.append(
                SvgPath(
                    d=d,
                    kind="path",
                    fill=p.fill,
                    stroke=p.stroke,
                    stroke_width=p.stroke_width,
                    stroke_dasharray=p.stroke_dasharray,
                )
            )
        elif p.kind == "circle":
            cx, cy, r = float(p.attrs["cx"]), float(p.attrs["cy"]), float(p.attrs["r"])
            # Approximate as ellipse polygon in room space
            steps = 24
            pts = [
                map_pt(cx + r * math.cos(2 * math.pi * i / steps), cy + r * math.sin(2 * math.pi * i / steps))
                for i in range(steps)
            ]
            d = "M " + " L ".join(f"{a:.4f} {b:.4f}" for a, b in pts) + " Z"
            out.append(
                SvgPath(
                    d=d,
                    kind="path",
                    fill=p.fill,
                    stroke=p.stroke,
                    stroke_width=p.stroke_width,
                    stroke_dasharray=p.stroke_dasharray,
                )
            )
        elif p.kind == "ellipse":
            cx, cy = float(p.attrs["cx"]), float(p.attrs["cy"])
            rx, ry = float(p.attrs["rx"]), float(p.attrs["ry"])
            steps = 24
            pts = [
                map_pt(cx + rx * math.cos(2 * math.pi * i / steps), cy + ry * math.sin(2 * math.pi * i / steps))
                for i in range(steps)
            ]
            d = "M " + " L ".join(f"{a:.4f} {b:.4f}" for a, b in pts) + " Z"
            out.append(
                SvgPath(
                    d=d,
                    kind="path",
                    fill=p.fill,
                    stroke=p.stroke,
                    stroke_width=p.stroke_width,
                    stroke_dasharray=p.stroke_dasharray,
                )
            )
        elif p.kind == "line":
            x1, y1 = map_pt(float(p.attrs["x1"]), float(p.attrs["y1"]))
            x2, y2 = map_pt(float(p.attrs["x2"]), float(p.attrs["y2"]))
            out.append(
                SvgPath(
                    d="",
                    kind="line",
                    fill=p.fill,
                    stroke=p.stroke,
                    stroke_width=p.stroke_width,
                    stroke_dasharray=p.stroke_dasharray,
                    attrs={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                )
            )
        else:
            # Path: transform absolute M/L/A numbers loosely by remapping M/L points only
            # Recipes emit simple M/L/A/Z; we transform M and L coordinates in pairs.
            out.append(_transform_path(p, map_pt))
    return out


def _transform_path(p: SvgPath, map_pt) -> SvgPath:
    tokens = p.d.replace(",", " ").split()
    out_tokens: list[str] = []
    i = 0
    cmd = "M"
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            out_tokens.append(cmd)
            i += 1
            continue
        if cmd in ("M", "L"):
            u, v = float(tokens[i]), float(tokens[i + 1])
            x, y = map_pt(u, v)
            out_tokens.extend([f"{x:.4f}", f"{y:.4f}"])
            i += 2
            cmd = "L" if cmd == "M" else cmd
        elif cmd == "A":
            # rx ry x-axis-rotation large-arc sweep x y
            rx, ry, rot, large, sweep = (tokens[i], tokens[i + 1], tokens[i + 2], tokens[i + 3], tokens[i + 4])
            u, v = float(tokens[i + 5]), float(tokens[i + 6])
            x, y = map_pt(u, v)
            # Keep radii in metres (approximate; rotation ignored for planning symbols)
            out_tokens.extend([rx, ry, rot, large, sweep, f"{x:.4f}", f"{y:.4f}"])
            i += 7
        elif cmd == "Z":
            i += 1
        else:
            out_tokens.append(t)
            i += 1
    return SvgPath(
        d=" ".join(out_tokens),
        kind="path",
        fill=p.fill,
        stroke=p.stroke,
        stroke_width=p.stroke_width,
        stroke_dasharray=p.stroke_dasharray,
    )


def _element(p: SvgPath) -> str:
    style = f'fill="{p.fill}" stroke="{p.stroke}" stroke-width="{p.stroke_width}"'
    if p.stroke_dasharray:
        style += f' stroke-dasharray="{p.stroke_dasharray}"'
    if p.kind == "rect":
        a = p.attrs
        return f'<rect x="{a["x"]}" y="{a["y"]}" width="{a["width"]}" height="{a["height"]}" {style} />'
    if p.kind == "circle":
        a = p.attrs
        return f'<circle cx="{a["cx"]}" cy="{a["cy"]}" r="{a["r"]}" {style} />'
    if p.kind == "ellipse":
        a = p.attrs
        return f'<ellipse cx="{a["cx"]}" cy="{a["cy"]}" rx="{a["rx"]}" ry="{a["ry"]}" {style} />'
    if p.kind == "line":
        a = p.attrs
        return f'<line x1="{a["x1"]}" y1="{a["y1"]}" x2="{a["x2"]}" y2="{a["y2"]}" {style} />'
    return f'<path d="{p.d}" {style} />'


def document(
    paths: Iterable[SvgPath],
    *,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    pad: float = 0.1,
) -> str:
    """SVG with Y flipped so plan +Y reads upward on screen."""
    width = max(max_x - min_x, 0.01) + 2 * pad
    height = max(max_y - min_y, 0.01) + 2 * pad
    # Flip Y: translate then scale
    ox = min_x - pad
    oy = max_y + pad
    body = "\n".join(_element(p) for p in paths)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width * 100:.1f}mm" height="{height * 100:.1f}mm" '
        f'viewBox="0 0 {width:.4f} {height:.4f}">\n'
        f'<g transform="translate({-ox:.4f} {oy:.4f}) scale(1 -1)">\n'
        f"{body}\n"
        f"</g>\n</svg>\n"
    )
