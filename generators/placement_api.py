"""MCP-ready facade for component lookup and room placement.

The public catalog MCP at pragmaticbim.ch stays read-only until a host mounts
these callables. Tool contract:

| Tool | Arguments | Returns |
| --- | --- | --- |
| ``get_component`` | ``id`` or ``slug`` | Component YAML dict (incl. optional media links) |
| ``list_components`` | optional ``category`` | List of ``{id, code, name, category, plan_symbol, picture_link, attachment_link}`` |
| ``preview_component`` | ``id``, optional ``params`` | ``{svg, ifc_bytes}`` at those parameters |
| ``place_room_layout`` | ``outline``, ``openings``, ``room_type``, … | ``{ifc_bytes, svg, unplaced, issues}`` |

Placement always uses ``representation.plan_symbol`` + parameters; media links
are catalog previews only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

from generators import room_rules as rr
from generators.component_geometry import component_plan_svg
from generators.component_geometry.preview import preview_ifc
from generators.room_layout import OpeningSpec, generate_room_layout

REPO_ROOT = Path(__file__).resolve().parents[1]


def _slug_to_id(ref: str) -> str:
    if ref.startswith("pragmaticbim:component/"):
        return ref
    return f"pragmaticbim:component/{ref}"


def get_component(ref: str) -> dict[str, Any]:
    """Load one component by id or slug."""
    return dict(rr.component(_slug_to_id(ref)))


def list_components(category: str | None = None) -> list[dict[str, Any]]:
    """Summaries for catalog browsing / MCP list tools."""
    rows: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / "components").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if category and data.get("category") != category:
            continue
        rows.append(
            {
                "id": data["id"],
                "code": data["code"],
                "name": data["name"],
                "category": data["category"],
                "plan_symbol": data["representation"]["plan_symbol"],
                "body": data["representation"]["body"],
                "picture_link": data.get("picture_link"),
                "attachment_link": data.get("attachment_link"),
            }
        )
    return rows


def preview_component(
    ref: str,
    params: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Generate SVG + IFC for a component at default or overridden parameters."""
    component = get_component(ref)
    if params:
        # Build a shallow copy with overridden defaults for preview
        overridden = {
            **component,
            "parameters": {
                key: {**spec, "default": float(params[key])} if key in params else spec
                for key, spec in component["parameters"].items()
            },
        }
        component = overridden
    return {
        "id": component["id"],
        "svg": component_plan_svg(component),
        "ifc_bytes": preview_ifc(component),
        "plan_symbol": component["representation"]["plan_symbol"],
        "picture_link": component.get("picture_link"),
        "attachment_link": component.get("attachment_link"),
    }


def place_room_layout(
    outline: Sequence[Sequence[float]],
    openings: Sequence[OpeningSpec | dict[str, Any]],
    room_type: str,
    *,
    configuration_id: str | None = None,
    edge_kinds: Sequence[str] | None = None,
    selection: dict[str, Iterable[str]] | None = None,
    space_name: str = "1.01",
    wall_height: float = 2.6,
    language: str = "de",
    project_name: str = "Raumlayout",
    include_clearances: bool = False,
) -> dict[str, Any]:
    """Place a room-type configuration and return IFC bytes + plan SVG + issues."""
    result = generate_room_layout(
        outline,
        openings,
        room_type,
        configuration_id=configuration_id,
        edge_kinds=edge_kinds,
        selection=selection,
        space_name=space_name,
        wall_height=wall_height,
        language=language,
        project_name=project_name,
        plan_svg=True,
        include_clearances=include_clearances,
    )
    return {
        "ifc_bytes": result.ifc_file.to_string().encode("utf-8"),
        "svg": result.plan_svg,
        "unplaced": [
            {"entry_id": u.entry_id, "index": u.index, "reason": u.reason} for u in result.unplaced
        ],
        "issues": [
            {
                "rule_id": issue.rule_id,
                "severity": issue.severity,
                "relation": issue.relation,
                "ok": issue.ok,
                "message": issue.message,
                "measured": issue.measured,
            }
            for issue in result.issues
        ],
        "space_global_id": result.space.GlobalId,
    }
