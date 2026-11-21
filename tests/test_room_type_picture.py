"""Room-type pictures: sample room, IFC with clearance proxies, annotated plan and runner flags."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

import runner
from generators import room_rules as rr
from generators.room_type_picture import (
    CLEARANCE_OBJECT_TYPE,
    generate_room_type_picture,
    write_room_type_picture,
)
from generators.sample_room import DEFAULT_AREA, MAX_AREA, sample_room
from render.plan import COLOR_FAIL, COLOR_OK, build_annotated_plan_svg

SVG = "{http://www.w3.org/2000/svg}"
SWITCH_ENTRY = "pragmaticbim:room-type-equipment/buero-default-lichtschalter"


@pytest.fixture(scope="module")
def buero():
    return generate_room_type_picture("buero")


def _rule_ids(config: dict) -> set[str]:
    return {
        rule["id"] for _, entry in rr.configuration_entries(config) for rule in entry.get("placement_rules") or []
    }


def _groups(svg: str, css_class: str) -> list[ET.Element]:
    root = ET.fromstring(svg)
    return [g for g in root.iter(f"{SVG}g") if g.get("class") == css_class]


# ── Sample room ──────────────────────────────────────────────────────────────


def test_sample_room_follows_net_planned_area() -> None:
    config = rr.configuration(rr.room_type("buero"))
    sample = sample_room(config)
    assert sample.area == pytest.approx(12.0)
    assert sorted(spec.function for spec in sample.openings) == ["access", "daylight"]
    assert {spec.function: spec.edge for spec in sample.openings} == {"access": 0, "daylight": 2}


def test_sample_room_without_area_uses_default() -> None:
    config = {**rr.configuration(rr.room_type("buero")), "attribute_presets": []}
    assert sample_room(config).area == pytest.approx(DEFAULT_AREA, rel=0.05)


def test_sample_room_caps_halls() -> None:
    config = rr.configuration(rr.room_type("aula"))
    assert sample_room(config).area == pytest.approx(MAX_AREA, abs=0.5)


def test_sample_layout_overrides_the_derived_room() -> None:
    layout = {
        "outline": [[0, 0], [8, 0], [8, 2], [0, 2]],
        "openings": [{"function": "access", "edge": 0, "offset": 1.0}],
    }
    config = {**rr.configuration(rr.room_type("buero")), "sample_layout": layout}
    sample = sample_room(config)
    assert sample.outline == [(0.0, 0.0), (8.0, 0.0), (8.0, 2.0), (0.0, 2.0)]
    assert [(spec.function, spec.edge, spec.offset) for spec in sample.openings] == [("access", 0, 1.0)]


# ── IFC ──────────────────────────────────────────────────────────────────────


def test_buero_ifc_has_space_furniture_and_clearance_proxies(buero) -> None:
    ifc_file = buero.ifc_file
    assert len(ifc_file.by_type("IfcSpace")) == 1
    assert len(ifc_file.by_type("IfcFurniture")) == 3
    assert ifc_file.by_type("IfcDoor") and ifc_file.by_type("IfcWindow")
    proxies = [p for p in ifc_file.by_type("IfcBuildingElementProxy") if p.ObjectType == CLEARANCE_OBJECT_TYPE]
    assert proxies and len(proxies) == len(buero.clearances)
    assert len(proxies) == sum(len(item.clearances) for item in buero.layout.items)


def test_buero_places_everything_it_orders(buero) -> None:
    assert buero.unplaced == []
    assert buero.result.issues == []


# ── Plan ─────────────────────────────────────────────────────────────────────


def test_buero_plan_lists_every_rule_in_the_legend(buero) -> None:
    ids = {row.get("data-rule-id") for row in _groups(buero.plan_svg, "legend-row")}
    assert ids == _rule_ids(buero.config)
    assert len(_groups(buero.plan_svg, "legend-row")) == len(buero.rule_results)


def test_buero_plan_annotates_every_rule_green(buero) -> None:
    annotations = _groups(buero.plan_svg, "rule-annotation")
    assert {a.get("data-rule-id") for a in annotations} == _rule_ids(buero.config)
    assert {a.get("data-status") for a in annotations} == {"ok"}
    assert COLOR_OK in buero.plan_svg and COLOR_FAIL not in buero.plan_svg


def test_next_to_and_distance_to_get_a_dimension_line(buero) -> None:
    for relation in ("next_to", "distance_to"):
        annotations = [a for a in _groups(buero.plan_svg, "rule-annotation") if a.get("data-relation") == relation]
        assert annotations, relation
        for annotation in annotations:
            assert annotation.findall(f"{SVG}text"), f"{relation} annotation has no value label"
    distance = next(
        a for a in _groups(buero.plan_svg, "rule-annotation") if a.get("data-relation") == "distance_to"
    )
    assert distance.findall(f"{SVG}line"), "distance_to has no dimension line"


def test_violated_rule_is_red(buero) -> None:
    layout = buero.layout
    switch = next(item for item in layout.items if item.entry_id == SWITCH_ENTRY)
    original = switch.frame
    try:
        switch.frame = replace(original, origin=(original.origin[0] + 2.0, original.origin[1] + 1.0))
        results = rr.evaluate_layout(layout, buero.config, include_passed=True)
        svg = build_annotated_plan_svg(layout, buero.config, results)
    finally:
        switch.frame = original
    failed = [r for r in results if not r.ok]
    assert failed
    annotations = {a.get("data-rule-id"): a for a in _groups(svg, "rule-annotation")}
    for result in failed:
        annotation = annotations[result.rule_id]
        assert annotation.get("data-status") == "fail"
        assert COLOR_FAIL in ET.tostring(annotation, encoding="unicode")
    rows = {row.get("data-rule-id"): row for row in _groups(svg, "legend-row")}
    assert rows[failed[0].rule_id].get("data-status") == "fail"


# ── Files and runner ─────────────────────────────────────────────────────────


def test_write_room_type_picture_writes_ifc_and_plan_svg(buero, tmp_path) -> None:
    written = write_room_type_picture(buero, tmp_path, isometric=False)
    assert written["ifc"].name == "buero-default.ifc" and written["ifc"].stat().st_size > 0
    assert written["plan_svg"].name == "buero-default-plan.svg"
    ET.fromstring(written["plan_svg"].read_text(encoding="utf-8"))
    try:
        import cairosvg  # noqa: F401
    except ImportError:
        assert "plan_png" not in written
    else:
        assert written["plan_png"].stat().st_size > 0


def test_room_type_without_equipment_still_gets_a_picture(tmp_path) -> None:
    picture = generate_room_type_picture("abfallschacht")
    assert picture.layout.items == [] and picture.rule_results == []
    assert picture.ifc_file.by_type("IfcSpace")
    written = write_room_type_picture(picture, tmp_path, isometric=False)
    ET.fromstring(written["plan_svg"].read_text(encoding="utf-8"))


def test_runner_rejects_unknown_room_type(tmp_path, capsys) -> None:
    assert runner.main(["--only-room-type", "gibt-es-nicht", "--output-dir", str(tmp_path)]) == 1
    assert "No room type" in capsys.readouterr().err
