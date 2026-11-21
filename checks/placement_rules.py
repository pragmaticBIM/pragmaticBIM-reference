"""Check the placement rules of room-type equipment and openings in an IFC model.

For every IfcSpace whose room type can be resolved, the checker reads the room
outline, its walls, doors, windows and equipment with IfcOpenShell geometry,
builds the same :class:`generators.room_rules.Layout` the generator works on and
evaluates the configuration's placement rules with the shared module.

Resolution, in order:

- Room type: ``room_types`` argument (space GlobalId or Name → room type slug),
  then a room type id, slug or code in ObjectType / Name / LongName / Description,
  then a unique match of LongName or Name against room type names and LongName presets.
- Equipment: elements contained in or referenced by the space, plus elements of
  the storey whose plan centre lies in the space. Each is matched to an entry by
  the IFC class of its component's element and the component's PredefinedType;
  Name / ObjectType equal to a component name breaks ties.
- Openings: IfcDoor / IfcWindow bodies within a wall thickness of a space edge.
  Edge kinds come from the nearest IfcWall (``Pset_WallCommon.IsExternal``).
- Front and width axis of an element: the X and Y axes of its object placement,
  as written by the generator. Door hinge sides come from ``OperationType``.

Usage: ``python -m checks.placement_rules model.ifc [--room-type GUID=buero ...]``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as element_util
import ifcopenshell.util.placement as placement_util
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from generators import room_rules as rr

_SKIPPED_CLASSES = ("IfcFeatureElement", "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow", "IfcCovering", "IfcSpace")


def _settings() -> ifcopenshell.geom.settings:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    return settings


class _Geometry:
    """World-coordinate vertices and faces per product, computed once."""

    def __init__(self) -> None:
        self._settings = _settings()
        self._cache: dict[int, tuple[np.ndarray, np.ndarray] | None] = {}

    def mesh(self, product) -> tuple[np.ndarray, np.ndarray] | None:
        if product.id() not in self._cache:
            try:
                shape = ifcopenshell.geom.create_shape(self._settings, product)
            except Exception:
                self._cache[product.id()] = None
            else:
                verts = np.asarray(shape.geometry.verts, dtype=float).reshape(-1, 3)
                faces = np.asarray(shape.geometry.faces, dtype=int).reshape(-1, 3)
                self._cache[product.id()] = (verts, faces) if len(verts) else None
        return self._cache[product.id()]

    def plan(self, product) -> Polygon | None:
        """Plan outline: union of the body's triangles projected to XY."""
        mesh = self.mesh(product)
        if mesh is None:
            return None
        verts, faces = mesh
        triangles = [Polygon(verts[face, :2]) for face in faces]
        triangles = [t for t in triangles if t.is_valid and t.area > 1e-9]
        if not triangles:
            return None
        merged = unary_union(triangles).buffer(1e-6).buffer(-1e-6)
        if merged.geom_type == "MultiPolygon":
            merged = max(merged.geoms, key=lambda g: g.area)
        return Polygon(merged.exterior).simplify(1e-3)


def _x_axis(product) -> tuple[float, float]:
    matrix = placement_util.get_local_placement(product.ObjectPlacement)
    x = matrix[:2, 0]
    if np.hypot(*x) < 1e-6:
        return (1.0, 0.0)
    return (float(x[0]), float(x[1]))


def _strings(*values: Any) -> list[str]:
    return [str(v).strip() for v in values if v not in (None, "") and str(v).strip()]


def _localized_values(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {str(v) for v in value.values()}
    return {str(value)} if value not in (None, "") else set()


def resolve_room_type(space, room_types: dict[str, str] | None = None) -> dict[str, Any] | None:
    """The room type of an IfcSpace, or None when it cannot be resolved unambiguously."""
    for key in (space.GlobalId, space.Name):
        if room_types and key in room_types:
            return rr.room_type(room_types[key])
    values = _strings(space.ObjectType, space.Name, space.LongName, getattr(space, "Description", None))
    for data in rr.room_types().values():
        keys = {data["id"], data["id"].split("/")[-1], data.get("code")}
        if any(value in keys for value in values):
            return data
    names = set(_strings(space.LongName, space.Name))
    matches = []
    for data in rr.room_types().values():
        known = _localized_values(data.get("name"))
        for config in data.get("configurations") or []:
            for preset in config.get("attribute_presets") or []:
                if preset.get("name") == "LongName":
                    known |= _localized_values(preset.get("value"))
        if names & known:
            matches.append(data)
    return matches[0] if len(matches) == 1 else None


def _operation_type(product) -> str | None:
    value = getattr(product, "OperationType", None)
    if value in (None, "NOTDEFINED", "USERDEFINED"):
        product_type = element_util.get_type(product)
        value = getattr(product_type, "OperationType", None) if product_type else None
    return value


def _match_entry(product, entries: list[dict[str, Any]]) -> tuple[dict[str, Any], str] | None:
    predefined = element_util.get_predefined_type(product)
    labels = set(_strings(product.Name, getattr(product, "ObjectType", None)))
    operation = _operation_type(product) or ""
    best: tuple[int, dict[str, Any], str] | None = None
    for entry in entries:
        for component_id in entry["components"]:
            component = rr.component(component_id)
            if not product.is_a(rr.element_ifc_class(component)):
                continue
            wanted = component.get("predefined_type")
            if wanted and predefined and predefined not in (wanted, "NOTDEFINED", "USERDEFINED"):
                continue
            score = 1 + (wanted == predefined)
            names = _localized_values(component.get("name")) | _localized_values(component.get("object_type"))
            if any(label == name or label.startswith(f"{name} ") for label in labels for name in names):
                score += 2
            if operation:
                swings = any(c["side"] == "swing" for c in component.get("clearances") or [])
                score += swings == ("SWING" in operation)
            if best is None or score > best[0]:
                best = (score, entry, component_id)
    return (best[1], best[2]) if best else None


def _measured_params(component: dict[str, Any], entry: dict[str, Any], frame: rr.Frame) -> dict[str, float]:
    params = rr.component_parameters(component, entry.get("params"))
    for key in ("width", "clear_width"):
        if key in params:
            params[key] = frame.width
    if "depth" in params and component["placement"]["host"] != "wall_opening":
        params["depth"] = frame.depth
    return params


def _placed(
    product,
    kind: str,
    match: tuple[dict[str, Any], str],
    geometry: _Geometry,
    floor: float,
) -> rr.Placed | None:
    mesh = geometry.mesh(product)
    if mesh is None:
        return None
    verts = mesh[0]
    entry, component_id = match
    component = rr.component(component_id)
    frame = rr.Frame.from_points(verts[:, :2], _x_axis(product))
    return rr.Placed(
        key=product.GlobalId,
        kind=kind,
        function=entry["function"],
        frame=frame,
        z_min=float(verts[:, 2].min()) - floor,
        z_max=float(verts[:, 2].max()) - floor,
        entry_id=entry["id"],
        component_id=component_id,
        clearances=rr.clearance_polygons(component, _measured_params(component, entry, frame), frame),
    )


def _edge_kinds(room_outline: Polygon, walls: list[tuple[Polygon, bool]]) -> list[str]:
    coords = list(room_outline.exterior.coords)[:-1]
    kinds = []
    for i, start in enumerate(coords):
        end = coords[(i + 1) % len(coords)]
        middle = Point((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        near = [(plan.distance(middle), external) for plan, external in walls]
        near = [item for item in near if item[0] <= 2 * rr.WALL_TOLERANCE]
        kinds.append("exterior" if near and min(near)[1] else "interior")
    return kinds


def _space_members(space) -> list:
    members = []
    for rel in getattr(space, "ContainsElements", None) or []:
        members.extend(rel.RelatedElements)
    for rel in getattr(space, "ReferencesElements", None) or []:
        members.extend(rel.RelatedElements)
    return members


def extract_layout(
    ifc_file: ifcopenshell.file,
    space,
    config: dict[str, Any],
    geometry: _Geometry | None = None,
) -> rr.Layout | None:
    """The space as a :class:`rr.Layout`: outline, edge kinds, openings and matched equipment."""
    geometry = geometry or _Geometry()
    outline = geometry.plan(space)
    mesh = geometry.mesh(space)
    if outline is None or mesh is None:
        return None
    floor, top = float(mesh[0][:, 2].min()), float(mesh[0][:, 2].max())

    walls = []
    for wall in ifc_file.by_type("IfcWall"):
        plan = geometry.plan(wall)
        if plan is not None and plan.distance(outline) <= 2 * rr.WALL_TOLERANCE:
            external = bool(element_util.get_psets(wall).get("Pset_WallCommon", {}).get("IsExternal"))
            walls.append((plan, external))
    room = rr.Room(list(outline.exterior.coords), _edge_kinds(outline, walls))

    entries = list(rr.configuration_entries(config))
    opening_entries = [e for kind, e in entries if kind == "opening"]
    equipment_entries = [e for kind, e in entries if kind == "equipment"]
    items: list[rr.Placed] = []

    for product in [*ifc_file.by_type("IfcDoor"), *ifc_file.by_type("IfcWindow")]:
        mesh = geometry.mesh(product)
        if mesh is None or mesh[0][:, 2].max() < floor or mesh[0][:, 2].min() > top:
            continue
        match = _match_entry(product, opening_entries)
        if match is None:
            continue
        item = _placed(product, "opening", match, geometry, floor)
        edge = rr.opening_edge(item.frame, room) if item else None
        if edge is None:
            continue
        item.edge_index = edge.index
        item.hinge_end = rr.hinge_end(item.frame, _operation_type(product), edge)
        items.append(item)

    members = {m.id(): m for m in _space_members(space)}
    container = element_util.get_container(space) or element_util.get_aggregate(space)
    if container is not None:
        inside = room.polygon.buffer(rr.WALL_TOLERANCE)
        for product in element_util.get_decomposition(container):
            if product.id() in members or not product.is_a("IfcElement") or product.is_a("IfcSpace"):
                continue
            if element_util.get_container(product) not in (container, None):
                continue
            mesh = geometry.mesh(product) if _match_entry(product, equipment_entries) else None
            if mesh is None:
                continue
            verts = mesh[0]
            centre = Point(float(verts[:, 0].mean()), float(verts[:, 1].mean()))
            if inside.contains(centre) and verts[:, 2].min() < top and verts[:, 2].max() > floor:
                members[product.id()] = product
    for product in members.values():
        if any(product.is_a(cls) for cls in _SKIPPED_CLASSES):
            continue
        match = _match_entry(product, equipment_entries)
        item = _placed(product, "equipment", match, geometry, floor) if match else None
        if item is not None:
            items.append(item)
    return rr.Layout(room, items, key=space.GlobalId)


def check_placement_rules(
    model: ifcopenshell.file | str | Path,
    room_types: dict[str, str] | None = None,
    *,
    configurations: dict[str, str] | None = None,
    include_passed: bool = False,
) -> list[rr.RuleResult]:
    """Evaluate the placement rules of every resolvable space in ``model``.

    ``room_types`` maps a space GlobalId or Name to a room type slug;
    ``configurations`` maps a space GlobalId to a configuration id (default:
    the room type's first active configuration). Returns the rules that are
    not met (or all evaluated rules with ``include_passed``).
    """
    ifc_file = model if isinstance(model, ifcopenshell.file) else ifcopenshell.open(str(model))
    geometry = _Geometry()
    results: list[rr.RuleResult] = []
    for space in ifc_file.by_type("IfcSpace"):
        data = resolve_room_type(space, room_types)
        if data is None:
            continue
        config = rr.configuration(data, (configurations or {}).get(space.GlobalId))
        if not any(entry.get("placement_rules") for _, entry in rr.configuration_entries(config)):
            continue
        layout = extract_layout(ifc_file, space, config, geometry)
        if layout is not None:
            results.extend(rr.evaluate_layout(layout, config, include_passed=include_passed))
    return results


def _parse_room_types(values: Iterable[str]) -> dict[str, str]:
    mapping = {}
    for value in values:
        key, _, slug = value.partition("=")
        if not slug:
            raise SystemExit(f"--room-type expects SPACE=ROOM_TYPE, got {value!r}")
        mapping[key] = slug
    return mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model", type=Path)
    parser.add_argument("--room-type", action="append", default=[], metavar="SPACE=ROOM_TYPE")
    args = parser.parse_args(argv)
    results = check_placement_rules(args.model, _parse_room_types(args.room_type))
    for result in results:
        print(f"{result.severity:9} {result.rule_id} {result.element} measured={result.measured} {result.message}")
    return 1 if any(r.severity == "required" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
