"""Point-cloud model picture: amber scan dots on a white building."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from generators.point_cloud import POINT_NAME, generate_point_cloud

ROOT = Path(__file__).resolve().parents[1]


def test_point_cloud_scene_accents_the_scan() -> None:
    ifc_file, cloud = generate_point_cloud()
    assert cloud.Name == POINT_NAME
    assert cloud.Representation is not None
    named = [
        product
        for product in ifc_file.by_type("IfcProduct")
        if getattr(product, "Name", None) == POINT_NAME
    ]
    assert named == [cloud]


def test_point_cloud_picture_is_published() -> None:
    png = ROOT / "media" / "images" / "model-point-cloud.png"
    tif = ROOT / "media" / "images" / "model-point-cloud-print.tif"
    assert png.is_file()
    assert tif.is_file()
    with Image.open(png) as image:
        assert image.size == (1024, 1024)
        orange = 0
        for y in range(0, image.height, 4):
            for x in range(0, image.width, 4):
                red, green, blue = image.getpixel((x, y))[:3]
                if red > 160 and red > green + 25 and blue < 140:
                    orange += 1
        assert orange > 200
