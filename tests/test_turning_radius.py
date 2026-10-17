import math
import sys
from pathlib import Path

from ifcopenshell.util.element import get_psets
from shapely.geometry import LineString, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generators import turning_radius as tr


def _default_envelope(*, simplify_tolerance: float) -> Polygon:
    poses = tr._vehicle_poses(
        outer_radius=tr.DEFAULT_PROXY_OUTER,
        vehicle_width=tr.DEFAULT_VEHICLE_WIDTH,
        vehicle_length=tr.DEFAULT_VEHICLE_LENGTH,
        nose_length=tr.DEFAULT_NOSE_LENGTH,
        inner_mid=tr.DEFAULT_PROXY_INNER_MID,
        approach=tr.DEFAULT_APPROACH,
        turn_angle=math.radians(tr.DEFAULT_TURN_ANGLE_DEG),
        pose_count=tr.DEFAULT_POSE_COUNT,
    )
    return Polygon(
        tr._union_polyline(
            poses,
            simplify_tolerance=simplify_tolerance,
        )
    )


def _inner_radius(envelope: Polygon, angle_deg: int) -> float:
    angle = math.radians(angle_deg)
    ray = LineString(
        [
            (0.0, 0.0),
            (30.0 * math.cos(angle), 30.0 * math.sin(angle)),
        ]
    )
    intersection = envelope.intersection(ray)
    radii: list[float] = []
    for geometry in getattr(intersection, "geoms", [intersection]):
        if geometry.geom_type == "LineString":
            radii.extend(math.hypot(x, y) for x, y in geometry.coords)
    return min(radius for radius in radii if radius > 1e-6)


def test_default_envelope_is_valid_smooth_and_area_preserving() -> None:
    raw = _default_envelope(simplify_tolerance=0.0)
    envelope = _default_envelope(
        simplify_tolerance=tr.DEFAULT_ENVELOPE_SIMPLIFY
    )

    assert envelope.is_valid
    assert envelope.geom_type == "Polygon"
    assert len(envelope.exterior.coords) - 1 <= 30
    assert abs(envelope.area / raw.area - 1.0) < 0.01

    inner_radii = [_inner_radius(envelope, angle) for angle in range(15, 121)]
    adjacent_changes = [
        abs(radius_b - radius_a)
        for radius_a, radius_b in zip(inner_radii, inner_radii[1:])
    ]
    assert max(adjacent_changes) < 0.20


def test_default_proxy_is_four_metres_high_with_matching_volume() -> None:
    _ifc_file, proxy = tr.generate_turning_radius()

    body = proxy.Representation.Representations[0]
    extrusion = body.Items[0]
    assert extrusion.is_a("IfcExtrudedAreaSolid")
    assert extrusion.Depth == 4.0

    quantities = get_psets(proxy)["Qto_BuildingElementProxyBaseQuantities"]
    envelope = _default_envelope(
        simplify_tolerance=tr.DEFAULT_ENVELOPE_SIMPLIFY
    )
    assert quantities["GrossVolume"] == round(envelope.area * 4.0, 3)
