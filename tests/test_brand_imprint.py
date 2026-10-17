"""The carved wordmark uses one camera-frame size on every picture."""

from __future__ import annotations

import numpy as np

from render.isometric import (
    _BRAND_GLYPH_Y_SCALE,
    _BRAND_WIDTH_FRAC,
    _brand_stamp_width_m,
    _horizontal_glyph_y_scale,
    _view_forward,
)


def _bounds(size: float, height: float | None = None) -> np.ndarray:
    return np.array(
        [[0.0, 0.0, 0.0], [size, size, size if height is None else height]],
        dtype=np.float64,
    )


def test_stamp_width_tracks_the_framed_view() -> None:
    small = _brand_stamp_width_m(
        _bounds(4.0),
        width_px=1024,
        height_px=1024,
        camera_padding=1.6,
    )
    large = _brand_stamp_width_m(
        _bounds(40.0),
        width_px=1024,
        height_px=1024,
        camera_padding=1.6,
    )

    assert abs(large / small - 10.0) < 1e-6
    assert 0.05 < small < 4.0


def test_uncropped_stamp_is_a_fixed_fraction_of_the_view() -> None:
    bounds = _bounds(12.0, 8.0)
    uncropped = _brand_stamp_width_m(
        bounds,
        width_px=1024,
        height_px=1200,
        camera_padding=2.0,
        fit_content=False,
    )
    view_width = _view_width(bounds, 2.0, 1024 / 1200)
    assert abs(uncropped / view_width - _BRAND_WIDTH_FRAC) < 1e-9

    fitted = _brand_stamp_width_m(
        bounds,
        width_px=1024,
        height_px=1200,
        camera_padding=2.0,
        fit_content=True,
    )
    assert fitted != uncropped
    assert fitted > 0.0


def test_print_and_catalog_keep_the_same_world_size() -> None:
    bounds = _bounds(8.0, 3.0)
    catalog = _brand_stamp_width_m(
        bounds, width_px=1024, height_px=1024, camera_padding=1.6
    )
    print_master = _brand_stamp_width_m(
        bounds, width_px=1200, height_px=1200, camera_padding=1.6
    )
    assert abs(catalog - print_master) / catalog < 0.01


def test_horizontal_letters_match_a_facing_wall() -> None:
    forward = _view_forward(None)
    y_scale = _horizontal_glyph_y_scale(
        forward,
        np.array([1.0, 0.0, 0.0]),
        np.array([-1.0, -1.0, 0.0]),
    )
    assert y_scale > _BRAND_GLYPH_Y_SCALE
    assert y_scale < 1.5


def _view_width(bounds: np.ndarray, padding: float, aspect: float) -> float:
    from render.isometric import _YFOV, _view_radius_distance

    _radius, distance = _view_radius_distance(bounds, padding)
    return 2.0 * distance * float(np.tan(_YFOV * 0.5)) * aspect
