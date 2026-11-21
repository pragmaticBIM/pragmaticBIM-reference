"""Picture set for one room-type configuration: IFC, annotated plan and isometric.

``generate_room_type_picture`` builds a sample room (:mod:`generators.sample_room`),
lets :func:`generators.room_layout.generate_room_layout` place the equipment,
adds every clearance zone as ``IfcBuildingElementProxy`` with ObjectType
``Bewegungsfläche`` and evaluates the placement rules, met ones included.
``write_room_type_picture`` writes ``{config}.ifc``, ``{config}-plan.svg`` and,
where the libraries are available, ``{config}-plan.png`` (needs ``cairosvg``) and
the isometric ``{config}.png``.

Equipment that found no position is listed in :attr:`RoomTypePicture.unplaced`
and its rules show as violated in the plan; nothing is dropped silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import ifcopenshell

from generators import room_rules as rr
from generators.base import get_body_context
from generators.parts import add_extruded_product
from generators.room_layout import RoomLayoutResult, Unplaced, generate_room_layout
from generators.sample_room import SampleRoom, sample_room
from render.plan import build_annotated_plan_svg

CLEARANCE_OBJECT_TYPE = "Bewegungsfläche"
CLEARANCE_HEIGHT = 0.02
"""Thickness of a clearance proxy in metres; zones are floor areas."""


@dataclass
class RoomTypePicture:
    slug: str
    config: dict[str, Any]
    sample: SampleRoom
    result: RoomLayoutResult
    rule_results: list[rr.RuleResult]
    plan_svg: str
    clearances: list[ifcopenshell.entity_instance] = field(default_factory=list)

    @property
    def name(self) -> str:
        """File stem: the configuration id without its namespace, e.g. ``buero-default``."""
        return self.config["id"].rsplit("/", 1)[-1]

    @property
    def ifc_file(self) -> ifcopenshell.file:
        return self.result.ifc_file

    @property
    def layout(self) -> rr.Layout:
        return self.result.layout

    @property
    def unplaced(self) -> list[Unplaced]:
        return self.result.unplaced


def _add_clearance_proxies(
    ifc_file: ifcopenshell.file,
    layout: rr.Layout,
    *,
    language: str,
) -> list[ifcopenshell.entity_instance]:
    storey = ifc_file.by_type("IfcBuildingStorey")[0]
    body_context = get_body_context(ifc_file)
    proxies: list[ifcopenshell.entity_instance] = []
    for item in layout.items:
        if not item.component_id:
            continue
        component_name = rr.component(item.component_id)["name"]
        label = component_name.get(language) or next(iter(component_name.values()))
        for zone in item.clearances:
            proxy = add_extruded_product(
                ifc_file,
                ifc_class="IfcBuildingElementProxy",
                name=f"{CLEARANCE_OBJECT_TYPE} {label}",
                body_context=body_context,
                storey=storey,
                polyline=list(zone.exterior.coords)[:-1],
                thickness=CLEARANCE_HEIGHT,
                predefined_type="USERDEFINED",
            )
            proxy.ObjectType = CLEARANCE_OBJECT_TYPE
            proxies.append(proxy)
    return proxies


def generate_room_type_picture(
    slug: str,
    configuration_id: str | None = None,
    *,
    selection: dict[str, Iterable[str]] | None = None,
    language: str = "de",
) -> RoomTypePicture:
    """Sample room, placed equipment, clearance proxies and rule results of one configuration.

    ``slug`` is a room-type slug (``buero``); the first active configuration is
    used unless ``configuration_id`` names another.
    """
    room_type = rr.room_type(slug)
    config = rr.configuration(room_type, configuration_id)
    sample = sample_room(config)
    result = generate_room_layout(
        sample.outline,
        sample.openings,
        slug,
        configuration_id=config["id"],
        selection=selection,
        language=language,
        project_name=room_type["name"].get(language) or slug,
    )
    clearances = _add_clearance_proxies(result.ifc_file, result.layout, language=language)
    rule_results = rr.evaluate_layout(result.layout, config, include_passed=True)
    result.issues = [r for r in rule_results if not r.ok]
    plan_svg = build_annotated_plan_svg(result.layout, config, rule_results)
    return RoomTypePicture(slug, config, sample, result, rule_results, plan_svg, clearances)


def _plan_png(svg_path: Path, png_path: Path) -> bool:
    """Rasterize the plan with ``cairosvg`` when it is installed."""
    try:
        import cairosvg
    except ImportError:
        return False
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1600, background_color="white")
    return True


def write_room_type_picture(
    picture: RoomTypePicture,
    output_dir: str | Path,
    *,
    isometric: bool = True,
) -> dict[str, Path]:
    """Write IFC, plan SVG and optional PNGs; returns the paths written by kind.

    Keys: ``ifc``, ``plan_svg``, and when available ``plan_png`` and ``png``
    (isometric). The plan PNG needs ``cairosvg``; without it only the SVG is written.
    """
    from render.isometric import render_isometric  # heavy: pyrender, trimesh

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    written["ifc"] = out / f"{picture.name}.ifc"
    picture.ifc_file.write(str(written["ifc"]))

    written["plan_svg"] = out / f"{picture.name}-plan.svg"
    written["plan_svg"].write_text(picture.plan_svg, encoding="utf-8")
    plan_png = out / f"{picture.name}-plan.png"
    if _plan_png(written["plan_svg"], plan_png):
        written["plan_png"] = plan_png

    if isometric:
        png = out / f"{picture.name}.png"
        render_isometric(
            picture.ifc_file,
            png,
            primary_guids=[i.key for i in picture.layout.items if i.kind == "equipment"],
            dotted_guids=[p.GlobalId for p in picture.clearances],
        )
        written["png"] = png
    return written
