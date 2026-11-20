"""CLI: generate default-parameter SVG + IFC previews and attach to component YAML.

Usage::

    python -m generators.component_geometry.preview --wave1 --attach
    python -m generators.component_geometry.preview --component wc-wandhaengend --attach
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import yaml
from ifcopenshell.api.spatial import assign_container

from generators import room_rules as rr
from generators.base import create_project_shell, get_body_context
from generators.component_geometry import (
    WAVE1_CATEGORIES,
    build_body,
    component_plan_svg,
    known_symbols,
)
from generators.component_geometry.registry import get_recipe
from generators.component_geometry.symbols import RECIPES

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENTS_DIR = REPO_ROOT / "components"
MEDIA_IMAGES = REPO_ROOT / "media" / "images"
MEDIA_ATTACHMENTS = REPO_ROOT / "media" / "attachments"


def _slug(component_id: str) -> str:
    return component_id.split("/")[-1]


def _set_link(text: str, key: str, filename: str) -> str:
    pattern = re.compile(rf"^({re.escape(key)}\s*:\s*).*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(rf"\1{filename}", text, count=1)
    for anchor in ("representation", "status", "comment"):
        # Insert before status/comment, or after representation block end is hard;
        # insert before status when present.
        if anchor == "representation":
            continue
        m = re.search(rf"^({anchor}\s*:)", text, re.MULTILINE)
        if m:
            return text[: m.start()] + f"{key}: {filename}\n" + text[m.start() :]
    return text.rstrip() + f"\n{key}: {filename}\n"


def preview_ifc(component: dict) -> bytes:
    """Sample IFC with one product at the origin using default parameters."""
    params = rr.component_parameters(component)
    width = float(params.get("width", params.get("clear_width", 1.0)))
    if "depth" in params:
        depth = float(params["depth"])
    elif component.get("representation", {}).get("body") == "opening":
        depth = 0.1
    else:
        depth = 0.6
    height = float(params.get("height", params.get("clear_height", 1.0)))
    frame = rr.Frame((0.0, 0.0), (1.0, 0.0), width, depth)
    item = rr.Placed(
        key="preview",
        kind="opening" if component.get("representation", {}).get("body") == "opening" else "equipment",
        function=None,
        frame=frame,
        z_min=0.0,
        z_max=height,
        component_id=component["id"],
        hinge_end="start",
    )
    ifc_file, _project, _site, _building, storey, body_context = create_project_shell(
        f"preview-{_slug(component['id'])}", storey_name="EG"
    )
    body_context = get_body_context(ifc_file) or body_context
    product = build_body(ifc_file, body_context, item, component, language="de", name=component["name"]["de"])
    assign_container(ifc_file, relating_structure=storey, products=[product])
    return ifc_file.to_string().encode("utf-8")


def attach_component(component: dict, *, output_dir: Path | None = None) -> dict[str, Path]:
    slug = _slug(component["id"])
    svg_name = f"{slug}-plan.svg"
    ifc_name = f"{slug}.ifc"
    out = output_dir or REPO_ROOT / "output" / "components"
    out.mkdir(parents=True, exist_ok=True)
    svg_path = out / svg_name
    ifc_path = out / ifc_name
    svg_path.write_text(component_plan_svg(component), encoding="utf-8")
    ifc_path.write_bytes(preview_ifc(component))

    MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
    MEDIA_ATTACHMENTS.mkdir(parents=True, exist_ok=True)
    picture_dest = MEDIA_IMAGES / svg_name
    attachment_dest = MEDIA_ATTACHMENTS / ifc_name
    shutil.copy2(svg_path, picture_dest)
    shutil.copy2(ifc_path, attachment_dest)

    yaml_path = COMPONENTS_DIR / f"{slug}.yaml"
    text = yaml_path.read_text(encoding="utf-8")
    text = _set_link(text, "picture_link", svg_name)
    text = _set_link(text, "attachment_link", ifc_name)
    yaml_path.write_text(text, encoding="utf-8")
    return {"picture": picture_dest, "attachment": attachment_dest, "yaml": yaml_path, "svg": svg_path, "ifc": ifc_path}


def _load_components(*, categories: set[str] | None = None) -> list[dict]:
    items = []
    for path in sorted(COMPONENTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("status", "active") == "deprecated":
            continue
        if categories is not None and data.get("category") not in categories:
            continue
        items.append(data)
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Component 2D/3D preview generator")
    parser.add_argument("--component", help="Component slug (e.g. wc-wandhaengend)")
    parser.add_argument("--wave1", action="store_true", help="Wave 1 categories only")
    parser.add_argument("--all", action="store_true", help="Every active component")
    parser.add_argument("--attach", action="store_true", help="Copy to media/ and set YAML links")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--list-symbols", action="store_true")
    args = parser.parse_args(argv)

    if args.list_symbols:
        for symbol in sorted(known_symbols()):
            print(symbol)
        return 0

    if args.all:
        components = _load_components()
    elif args.wave1:
        components = _load_components(categories=set(WAVE1_CATEGORIES))
    elif args.component:
        path = COMPONENTS_DIR / f"{args.component}.yaml"
        components = [yaml.safe_load(path.read_text(encoding="utf-8"))]
    else:
        parser.error("pass --component SLUG, --wave1, or --all")
        return 2

    missing = [
        f"{_slug(c['id'])}:{c['representation']['plan_symbol']}"
        for c in components
        if c["representation"]["plan_symbol"] not in RECIPES
    ]
    if missing:
        raise SystemExit(f"components without recipes: {', '.join(missing)}")

    for component in components:
        symbol = component["representation"]["plan_symbol"]
        recipe = get_recipe(symbol)
        print(f"{_slug(component['id'])}: {symbol} ({type(recipe).__name__})")
        if args.attach:
            paths = attach_component(component, output_dir=args.output_dir)
            print(f"  → {paths['picture'].name}, {paths['attachment'].name}")
        else:
            out = args.output_dir or REPO_ROOT / "output" / "components"
            out.mkdir(parents=True, exist_ok=True)
            slug = _slug(component["id"])
            (out / f"{slug}-plan.svg").write_text(component_plan_svg(component), encoding="utf-8")
            (out / f"{slug}.ifc").write_bytes(preview_ifc(component))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
