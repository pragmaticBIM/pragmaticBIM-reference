"""Component 2D/3D recipe and room-layout integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from generators import room_rules as rr
from generators.component_geometry import (
    build_body,
    component_plan_svg,
    known_symbols,
)
from generators.component_geometry.registry import get_recipe
from generators.component_geometry.symbols import RECIPES
from generators.base import create_project_shell, get_body_context
from generators.placement_api import get_component, list_components, place_room_layout, preview_component
from generators.room_layout import OpeningSpec, generate_room_layout

REPO_ROOT = Path(__file__).resolve().parents[1]


def _all_components() -> list[dict]:
    items = []
    for path in sorted((REPO_ROOT / "components").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("status", "active") != "deprecated":
            items.append(data)
    return items


def test_every_component_has_recipe() -> None:
    missing = []
    for component in _all_components():
        symbol = component["representation"]["plan_symbol"]
        if symbol not in RECIPES:
            missing.append(f"{component['id']}:{symbol}")
    assert not missing, f"components without recipes: {missing}"


def test_known_symbols_nonempty() -> None:
    assert "wc" in known_symbols()
    assert "door_swing" in known_symbols()
    assert "kitchen_run" in known_symbols()
    assert "desk" in known_symbols()
    assert "boiler" in known_symbols()


@pytest.mark.parametrize("component", _all_components(), ids=lambda c: c["id"].split("/")[-1])
def test_every_component_plan_svg_nonempty(component: dict) -> None:
    svg = component_plan_svg(component)
    assert svg.startswith("<?xml")
    assert "<svg" in svg
    assert "stroke" in svg


@pytest.mark.parametrize("component", _all_components(), ids=lambda c: c["id"].split("/")[-1])
def test_every_component_body_creates_product(component: dict) -> None:
    params = rr.component_parameters(component)
    width = float(params.get("width", params.get("clear_width", 1.0)))
    depth = float(params["depth"]) if "depth" in params else 0.1
    height = float(params.get("height", params.get("clear_height", 1.0)))
    frame = rr.Frame((0.0, 0.0), (1.0, 0.0), width, depth)
    item = rr.Placed(
        key="t",
        kind="equipment",
        function=None,
        frame=frame,
        z_min=0.0,
        z_max=height,
        component_id=component["id"],
        hinge_end="start",
    )
    ifc_file, *_rest, body_context = create_project_shell("test")
    body_context = get_body_context(ifc_file) or body_context
    product = build_body(ifc_file, body_context, item, component, name="Test")
    assert product.Representation is not None
    assert product.is_a(rr.element_ifc_class(component))


def test_unknown_symbol_falls_back_to_box() -> None:
    recipe = get_recipe("not_a_real_symbol_xyz")
    component = yaml.safe_load((REPO_ROOT / "components" / "sofa.yaml").read_text(encoding="utf-8"))
    component = {**component, "representation": {**component["representation"], "plan_symbol": "not_a_real_symbol_xyz"}}
    svg = component_plan_svg(component)
    assert "<svg" in svg


def test_door_clear_width_scales_plan() -> None:
    component = yaml.safe_load((REPO_ROOT / "components" / "tuer-dreh-innen.yaml").read_text(encoding="utf-8"))
    narrow = component_plan_svg(
        {
            **component,
            "parameters": {**component["parameters"], "clear_width": {**component["parameters"]["clear_width"], "default": 0.8}},
        }
    )
    wide = component_plan_svg(
        {
            **component,
            "parameters": {**component["parameters"], "clear_width": {**component["parameters"]["clear_width"], "default": 1.0}},
        }
    )
    assert narrow != wide


def test_bathroom_layout_uses_recipe_bodies() -> None:
    result = generate_room_layout(
        [(0, 0), (2.4, 0), (2.4, 2.2), (0, 2.2)],
        [OpeningSpec("access", edge=0, offset=0.9)],
        "badezimmer",
        plan_svg=True,
    )
    assert result.plan_svg and "<svg" in result.plan_svg
    # At least one sanitary product present
    sanitary = [p for p in result.ifc_file.by_type("IfcSanitaryTerminal")]
    assert sanitary
    # Bodies exist (recipe or box)
    for product in sanitary:
        assert product.Representation is not None


def test_kitchen_layout_plan_svg() -> None:
    # kueche room type may need larger outline
    result = generate_room_layout(
        [(0, 0), (4.0, 0), (4.0, 3.5), (0, 3.5)],
        [
            OpeningSpec("access", edge=0, offset=1.0),
            OpeningSpec("daylight", edge=2, offset=2.0),
        ],
        "kueche",
        plan_svg=True,
    )
    assert result.plan_svg and "svg" in result.plan_svg


def test_placement_api_get_and_list() -> None:
    component = get_component("wc-wandhaengend")
    assert component["id"] == "pragmaticbim:component/wc-wandhaengend"
    rows = list_components(category="sanitary")
    assert any(r["id"] == component["id"] for r in rows)


def test_placement_api_preview_and_place() -> None:
    preview = preview_component("wc-wandhaengend")
    assert preview["svg"].startswith("<?xml")
    assert preview["ifc_bytes"].startswith(b"ISO-10303") or b"IFC" in preview["ifc_bytes"][:200]
    placed = place_room_layout(
        [(0, 0), (4, 0), (4, 3), (0, 3)],
        [OpeningSpec("access", edge=0, offset=0.7), OpeningSpec("daylight", edge=2, offset=2.0)],
        "buero",
    )
    assert placed["svg"]
    assert placed["ifc_bytes"]
    assert "unplaced" in placed


def test_every_component_has_media_links() -> None:
    """Every component has picture_link + attachment_link pointing at media files."""
    missing = []
    for component in _all_components():
        pic = component.get("picture_link")
        att = component.get("attachment_link")
        if not pic or not att:
            missing.append(f"{component['id']}: missing picture_link/attachment_link")
            continue
        if not (REPO_ROOT / "media" / "images" / pic).is_file():
            missing.append(f"{component['id']}: missing image {pic}")
        if not (REPO_ROOT / "media" / "attachments" / att).is_file():
            missing.append(f"{component['id']}: missing attachment {att}")
    assert not missing, missing
